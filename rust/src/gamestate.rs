use num_enum::{FromPrimitive, TryFromPrimitive};
use protobuf::Enum;
use pyo3::prelude::*;
use pyo3::types::IntoPyDict;
use std::{collections::{HashMap, BTreeMap}, hash::Hash};

use super::stormgate;

impl From<stormgate::LeaveReason> for LeaveReason {
    fn from(value: stormgate::LeaveReason) -> Self {
        (value.value() as u32).into()
    }
}

impl ToPyObject for stormgate::UUID {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        let int_repr = ((self.part1 as u128) << 64) + (self.part2 as u128);
        let uuid_mod = PyModule::import_bound(py, "uuid").unwrap();
        let kwargs = [("int", int_repr)].into_py_dict_bound(py);
        let result = uuid_mod.call_method("UUID", (), Some(&kwargs));
        match result {
            Ok(x) => x.to_object(py),
            Err(_) => py.None(),
        }
    }
}
impl IntoPy<Py<PyAny>> for stormgate::UUID {
    fn into_py(self, py: Python<'_>) -> Py<PyAny> {
        self.to_object(py)
    }
}
impl Eq for stormgate::UUID {}
impl Hash for stormgate::UUID {
    fn hash<H: std::hash::Hasher>(&self, state: &mut H) {
        self.part1.hash(state);
        self.part2.hash(state);
    }
}

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, TryFromPrimitive)]
#[repr(u32)]
pub enum SlotType {
    Closed = 0,
    Human = 1,
    Ai = 2,
}

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, TryFromPrimitive)]
#[repr(u32)]
pub enum Faction {
    Vanguard = 0,
    Infernals = 1,
    Celestial = 2,
    Blockade = 101,
    Amara = 102,
    Maloc = 201,
    Warz = 202,
    Auralanna = 301,
}

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, TryFromPrimitive)]
#[repr(u32)]
pub enum AIType {
    PeacefulBot = 0,
    MurderBotJr = 1,
    MurderBotSr = 2,
}

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, FromPrimitive)]
#[repr(u32)]
pub enum LeaveReason {
    #[default]
    Unknown = 0,
    Surrender = 1,
    Leave = 2,
    Disconnect = 3,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct Slot {
    #[pyo3(get)]
    pub slot_type: SlotType,
    #[pyo3(get)]
    pub faction: Faction,
    #[pyo3(get)]
    pub ai_type: Option<AIType>,
    #[pyo3(get)]
    pub client_id: Option<i32>,
}

impl Default for Slot {
    fn default() -> Self {
        Slot {
            // Stormgate lobby slots start with these values:
            slot_type: SlotType::Human,
            faction: Faction::Vanguard,
            ai_type: None,
            client_id: None,
        }
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct Client {
    #[pyo3(get)]
    pub uuid: stormgate::UUID,
    #[pyo3(get)]
    pub client_id: i32,
    #[pyo3(get)]
    pub nickname: Option<String>,
    #[pyo3(get)]
    pub discriminator: Option<String>,
    #[pyo3(get)]
    pub slot_number: Option<i32>, // 255 means spectator
    #[pyo3(get)]
    pub left_game_time: Option<i32>,
    #[pyo3(get)]
    pub left_game_reason: LeaveReason,
}
impl Client {
    pub fn new(client_id: i32, uuid: stormgate::UUID) -> Self {
        Client {
            client_id,
            uuid,
            nickname: None,
            discriminator: None,
            slot_number: None,
            left_game_reason: LeaveReason::Unknown,
            left_game_time: None,
        }
    }
}


#[pyclass]
#[derive(Debug, Clone)]
pub struct SlotAssignment {
    #[pyo3(get)]
    pub slot_number: i32,
    #[pyo3(get)]
    pub nickname: String,
}

#[pyclass]
#[derive(Debug, Clone, Default)]
pub struct GameState {
    #[pyo3(get)]
    pub map_name: Option<String>,
    #[pyo3(get)]
    pub slots: BTreeMap<i32, Slot>,
    #[pyo3(get)]
    pub clients: BTreeMap<i32, Client>,
    #[pyo3(get)]
    pub game_started: bool,
    #[pyo3(get)]
    pub game_started_time: Option<i32>,
    #[pyo3(get)]
    pub slot_assignments: HashMap<stormgate::UUID, SlotAssignment>,
}
