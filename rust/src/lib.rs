use flate2::read::GzDecoder;
use num_enum::TryFromPrimitive;
use protobuf::Message;
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use stormgate::MatchType;
use std::collections::BTreeMap;
use std::fs::File;
use std::io::{self, Read, Seek};
use varint_rs::VarintReader;
use log::debug;

mod stormgate;
use stormgate::replay_chunk::wrapper::replay_content::Content_type as CT;
use stormgate::lobby_change_slot::slot_choice::Choice_type;

mod gamestate;
use gamestate::*;

struct ReplayFile {
    decompressed_stream: GzDecoder<File>,
    pub build_number: i32,
}

impl ReplayFile {
    pub fn open(path: String) -> Result<Self, io::Error> {
        let mut f = File::open(path)?;
        f.seek(io::SeekFrom::Start(12))?;
        let build_number = {
            let mut buf = [0; 4];
            f.read_exact(&mut buf[..])?;
            i32::from_le_bytes(buf)
        };
        f.seek(io::SeekFrom::Start(16))?;

        let decompressed_stream = GzDecoder::new(f);
        Ok(Self {
            decompressed_stream,
            build_number,
        })
    }
}

impl Iterator for ReplayFile {
    type Item = stormgate::ReplayChunk;
    fn next(&mut self) -> Option<Self::Item> {
        // let len = self.decompressed_stream.read_usize_varint().ok()?;
        match self.decompressed_stream.read_usize_varint() {
            Ok(len) => {
                let mut buf = vec![0; len];
                self.decompressed_stream.read_exact(&mut buf).unwrap();
                Some(stormgate::ReplayChunk::parse_from_bytes(&buf).unwrap())
            }
            Err(e) => {
                debug!("Ending iteration: {}", e);
                None
            }
        }
    }
}

fn simulate(replay: ReplayFile) -> Result<GameState, String> {
    let mut state: GameState = Default::default();
    for chunk in replay {
        let timestamp = chunk.timestamp;
        let client_id = chunk.client_id;
        debug!("{} {}", timestamp, client_id);
        let Some(content) = take_content(chunk) else {
            continue;
        };
        match content {
            CT::MapDetails(m) => {
                state.map_name = Some(m.map_name);
                let slot_count = match m.match_type.enum_value_or_default() {
                    MatchType::Coop3vE => 3,
                    MatchType::Ranked1v1 => 2,
                    _ => 2,
                };
                debug!("Map has {slot_count} slots");
                for i in 1..=slot_count {
                    state.slots.insert(i, Default::default());
                }
            }
            CT::AssignPlayerSlot(mut m) => {
                let Some(uuid) = m.uuid.take() else { continue };
                state.slot_assignments.insert(
                    uuid,
                    SlotAssignment {
                        slot_number: m.slot,
                        nickname: m.nickname,
                    },
                );
            }
            CT::Player(mut m) => {
                let Some(uuid) = m.uuid.take() else {
                    continue;
                };
                let (nickname, discriminator) = match m.name.take() {
                    Some(c) => (Some(c.nickname), Some(c.discriminator)),
                    None => (None, None),
                };
                let mut client = Client {
                    client_id,
                    uuid,
                    discriminator,
                    nickname,
                    slot_number: None,
                    left_game_reason: LeaveReason::Unknown,
                    left_game_time: None,
                };
                if let Some(assignment) = state.slot_assignments.get(&client.uuid) {
                    client.slot_number = Some(assignment.slot_number);
                    let slot = state.slots.get_mut(&assignment.slot_number).unwrap();
                    slot.client_id = Some(client_id);
                }
                state.clients.insert(client_id, client);
            }
            CT::ClientConnected(mut m) => {
                let Some(uuid) = m.uuid.take() else {
                    continue;
                };
                let mut client = Client {
                    client_id: m.client_id,
                    uuid,
                    nickname: None,
                    discriminator: None,
                    slot_number: None,
                    left_game_reason: LeaveReason::Unknown,
                    left_game_time: None,
                };
                if let Some(assignment) = state.slot_assignments.get(&client.uuid) {
                    client.slot_number = Some(assignment.slot_number);
                    if client.nickname.is_none() {
                        client.nickname = Some(assignment.nickname.clone());
                    } else {
                        //assert_eq!(client.nickname.unwrap(), assignment.nickname);
                    }
                    if let Some(slot) = state.slots.get_mut(&assignment.slot_number) {
                        slot.client_id = Some(client.client_id);
                    }
                }
                state.clients.insert(client.client_id, client);
            }
            CT::PlayerLeftGame(m) => {
                if state.game_started {
                    if let Some(client) = state.clients.get_mut(&client_id) {
                        client.left_game_time = Some(timestamp);
                        client.left_game_reason = m.reason.enum_value_or_default().into();
                    }
                } else {
                    let client = state.clients.remove(&client_id);
                    let suffix = if let Some(c) = &client {
                        format!(": {} {}", c.nickname.clone().unwrap_or_default(), c.uuid)
                    } else {
                        String::new()
                    };
                    debug!("Removing player {}{}", client_id, suffix);
                    for slot in state.slots.values_mut() {
                        if slot.client_id == Some(client_id) {
                            slot.client_id = None;
                        }
                    }
                }
            }
            CT::ClientDisconnected(m) => {
                if state.game_started {
                    if let Some(client) = state.clients.get_mut(&m.client_id) {
                        if client.left_game_time.is_none() {
                            assert_eq!(client.uuid, m.player_uuid.unwrap());
                            client.left_game_time = Some(timestamp);
                            client.left_game_reason = m.reason.enum_value_or_default().into();
                        }
                    }
                }
            }
            CT::ChangeSlot(mut m) => {
                if state.slots.is_empty() {
                    return Err("Received slot change before map info?".into());
                }
                let Some(client) = state.clients.get_mut(&client_id) else {
                    return Err(format!("Unknown client {}", client_id))
                };
                if let Some(slot_number) = client.slot_number {
                    if slot_number != 255 {
                        if let Some(slot) = state.slots.get_mut(&slot_number) {
                            slot.client_id = None;
                        } else {
                            return Err(format!("Slot {} out of range", slot_number));
                        }
                    }
                }
                let choice = m.choice.take().and_then(|x| x.choice_type);
                let new_slot_number = match choice {
                    Some(Choice_type::SpecificSlot(c)) => c.slot,
                    _ => first_open_human_slot(&state.slots),
                };
                debug!("Putting client {} in slot {}", client_id, new_slot_number);
                client.slot_number = Some(new_slot_number);
                if new_slot_number != 255 {
                    if let Some(slot) = state.slots.get_mut(&new_slot_number) {
                        if slot.slot_type != SlotType::Human || slot.client_id.is_some() {
                            return Err("Client assigned to non-human or occupied slot?".into());
                        }
                        slot.client_id = Some(client_id);
                    } else {
                        return Err(format!("Slot {} out of range", new_slot_number));
                    }
                }
            }
            CT::SetVariable(m) => {
                let Some(slot) = state.slots.get_mut(&m.slot) else {
                    return Err(format!("Slot {} out of range", m.slot));
                };
                match m.variable_id {
                    374945738 => {
                        if let Ok(v) = SlotType::try_from_primitive(m.value) {
                            slot.slot_type = v;
                            debug!("Set slot[{}].type = {:?}", m.slot, v);
                            slot.ai_type = match v {
                                SlotType::Ai => Some(AIType::PeacefulBot),
                                _ => None,
                            };
                        }
                    }
                    2952722564 => {
                        if let Ok(v) = Faction::try_from_primitive(m.value) {
                            slot.faction = v;
                            debug!("Set slot[{}].faction = {:?}", m.slot, slot.faction);
                        }
                    }
                    655515685 => {
                        slot.ai_type = m.value.try_into().ok();
                        debug!("Set slot[{}].ai_type = {:?}", m.slot, slot.ai_type);
                    }
                    _ => {}
                }
            }
            CT::StartGame(_) => {
                state.game_started = true;
                state.game_started_time = Some(timestamp);
            }
        }
    }
    Ok(state)
}

#[pyfunction]
fn simulate_replay_file(path: String) -> PyResult<GameState> {
    let replay = ReplayFile::open(path)?;
    debug!("Build number: {}", replay.build_number);
    match simulate(replay) {
        Ok(state) => Ok(state),
        Err(s) => Err(PyRuntimeError::new_err(s)),
    }
}

fn take_content(mut chunk: stormgate::ReplayChunk) -> Option<CT> {
    chunk.inner.take()?.content.take()?.content_type
}

fn first_open_human_slot(slots: &BTreeMap<i32, Slot>) -> i32 {
    for (num, slot) in slots.iter() {
        if slot.client_id.is_none() && slot.slot_type == SlotType::Human {
            return *num;
        }
    }
    return 255;
}

/// A Python module implemented in Rust.
#[pymodule]
fn _replay(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();
    m.add_function(wrap_pyfunction!(simulate_replay_file, m)?)?;
    m.add_class::<gamestate::SlotType>()?;
    m.add_class::<gamestate::Faction>()?;
    m.add_class::<gamestate::AIType>()?;
    m.add_class::<gamestate::LeaveReason>()?;
    m.add_class::<gamestate::Slot>()?;
    m.add_class::<gamestate::Client>()?;
    m.add_class::<gamestate::SlotAssignment>()?;
    m.add_class::<gamestate::GameState>()?;
    Ok(())
}
