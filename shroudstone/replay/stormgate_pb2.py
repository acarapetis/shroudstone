# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: stormgate.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0fstormgate.proto\x12\tstormgate\"\xca\x05\n\x0bReplayChunk\x12\x11\n\ttimestamp\x18\x01 \x01(\x05\x12\x11\n\tclient_id\x18\x02 \x01(\x05\x12-\n\x05inner\x18\x03 \x01(\x0b\x32\x1e.stormgate.ReplayChunk.Wrapper\x1a\xe5\x04\n\x07Wrapper\x12=\n\x07\x63ontent\x18\x01 \x01(\x0b\x32,.stormgate.ReplayChunk.Wrapper.ReplayContent\x1a\x9a\x04\n\rReplayContent\x12,\n\x0bmap_details\x18\x03 \x01(\x0b\x32\x15.stormgate.MapDetailsH\x00\x12\x36\n\x10\x63lient_connected\x18\x04 \x01(\x0b\x32\x1a.stormgate.ClientConnectedH\x00\x12#\n\x06player\x18\x0c \x01(\x0b\x32\x11.stormgate.PlayerH\x00\x12\x31\n\x0b\x63hange_slot\x18\r \x01(\x0b\x32\x1a.stormgate.LobbyChangeSlotH\x00\x12\x33\n\x0cset_variable\x18\x0f \x01(\x0b\x32\x1b.stormgate.LobbySetVariableH\x00\x12*\n\nstart_game\x18\x12 \x01(\x0b\x32\x14.stormgate.StartGameH\x00\x12\x35\n\x10player_left_game\x18\x19 \x01(\x0b\x32\x19.stormgate.PlayerLeftGameH\x00\x12<\n\x13\x63lient_disconnected\x18\x1f \x01(\x0b\x32\x1d.stormgate.ClientDisconnectedH\x00\x12\x39\n\x12\x61ssign_player_slot\x18% \x01(\x0b\x32\x1b.stormgate.AssignPlayerSlotH\x00\x12*\n\nplayer_alt\x18- \x01(\x0b\x32\x14.stormgate.PlayerAltH\x00\x42\x0e\n\x0c\x63ontent_type\"n\n\nMapDetails\x12\x12\n\nmap_folder\x18\x01 \x01(\t\x12\x10\n\x08map_name\x18\x02 \x01(\t\x12\x10\n\x08map_seed\x18\x03 \x01(\x05\x12(\n\nmatch_type\x18\x07 \x01(\x0e\x32\x14.stormgate.MatchType\"C\n\x0f\x43lientConnected\x12\x11\n\tclient_id\x18\x01 \x01(\x05\x12\x1d\n\x04uuid\x18\x02 \x01(\x0b\x32\x0f.stormgate.UUID\"\x8a\x01\n\x06Player\x12\x1d\n\x04uuid\x18\x02 \x01(\x0b\x32\x0f.stormgate.UUID\x12*\n\x04name\x18\x03 \x01(\x0b\x32\x1c.stormgate.Player.PlayerName\x1a\x35\n\nPlayerName\x12\x10\n\x08nickname\x18\x01 \x01(\t\x12\x15\n\rdiscriminator\x18\x02 \x01(\t\"\xd1\x01\n\x0fLobbyChangeSlot\x12\x35\n\x06\x63hoice\x18\x01 \x01(\x0b\x32%.stormgate.LobbyChangeSlot.SlotChoice\x1a\x86\x01\n\nSlotChoice\x12K\n\rspecific_slot\x18\x02 \x01(\x0b\x32\x32.stormgate.LobbyChangeSlot.SlotChoice.SpecificSlotH\x00\x1a\x1c\n\x0cSpecificSlot\x12\x0c\n\x04slot\x18\x01 \x01(\x05\x42\r\n\x0b\x63hoice_type\"D\n\x10LobbySetVariable\x12\x0c\n\x04slot\x18\x03 \x01(\x05\x12\x13\n\x0bvariable_id\x18\x04 \x01(\r\x12\r\n\x05value\x18\x05 \x01(\r\"\x0b\n\tStartGame\"^\n\x0ePlayerLeftGame\x12$\n\x0bplayer_uuid\x18\x01 \x01(\x0b\x32\x0f.stormgate.UUID\x12&\n\x06reason\x18\x02 \x01(\x0e\x32\x16.stormgate.LeaveReason\"u\n\x12\x43lientDisconnected\x12\x11\n\tclient_id\x18\x01 \x01(\x05\x12&\n\x06reason\x18\x02 \x01(\x0e\x32\x16.stormgate.LeaveReason\x12$\n\x0bplayer_uuid\x18\x03 \x01(\x0b\x32\x0f.stormgate.UUID\"Q\n\x10\x41ssignPlayerSlot\x12\x1d\n\x04uuid\x18\x01 \x01(\x0b\x32\x0f.stormgate.UUID\x12\x0c\n\x04slot\x18\x02 \x01(\x03\x12\x10\n\x08nickname\x18\x03 \x01(\t\"w\n\tPlayerAlt\x12\x30\n\x04name\x18\x05 \x01(\x0b\x32\".stormgate.PlayerAlt.PlayerNameAlt\x1a\x38\n\rPlayerNameAlt\x12\x10\n\x08nickname\x18\x01 \x01(\t\x12\x15\n\rdiscriminator\x18\x02 \x01(\t\"$\n\x04UUID\x12\r\n\x05part1\x18\x01 \x01(\x04\x12\r\n\x05part2\x18\x02 \x01(\x04*I\n\tMatchType\x12\x14\n\x10UnknownMatchType\x10\x00\x12\n\n\x06\x43ustom\x10\x01\x12\r\n\tRanked1v1\x10\x02\x12\x0b\n\x07\x43oop3vE\x10\x03*J\n\x0bLeaveReason\x12\x11\n\rUnknownReason\x10\x00\x12\r\n\tSurrender\x10\x01\x12\t\n\x05Leave\x10\x02\x12\x0e\n\nDisconnect\x10\x03\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'stormgate_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _MATCHTYPE._serialized_start=1821
  _MATCHTYPE._serialized_end=1894
  _LEAVEREASON._serialized_start=1896
  _LEAVEREASON._serialized_end=1970
  _REPLAYCHUNK._serialized_start=31
  _REPLAYCHUNK._serialized_end=745
  _REPLAYCHUNK_WRAPPER._serialized_start=132
  _REPLAYCHUNK_WRAPPER._serialized_end=745
  _REPLAYCHUNK_WRAPPER_REPLAYCONTENT._serialized_start=207
  _REPLAYCHUNK_WRAPPER_REPLAYCONTENT._serialized_end=745
  _MAPDETAILS._serialized_start=747
  _MAPDETAILS._serialized_end=857
  _CLIENTCONNECTED._serialized_start=859
  _CLIENTCONNECTED._serialized_end=926
  _PLAYER._serialized_start=929
  _PLAYER._serialized_end=1067
  _PLAYER_PLAYERNAME._serialized_start=1014
  _PLAYER_PLAYERNAME._serialized_end=1067
  _LOBBYCHANGESLOT._serialized_start=1070
  _LOBBYCHANGESLOT._serialized_end=1279
  _LOBBYCHANGESLOT_SLOTCHOICE._serialized_start=1145
  _LOBBYCHANGESLOT_SLOTCHOICE._serialized_end=1279
  _LOBBYCHANGESLOT_SLOTCHOICE_SPECIFICSLOT._serialized_start=1236
  _LOBBYCHANGESLOT_SLOTCHOICE_SPECIFICSLOT._serialized_end=1264
  _LOBBYSETVARIABLE._serialized_start=1281
  _LOBBYSETVARIABLE._serialized_end=1349
  _STARTGAME._serialized_start=1351
  _STARTGAME._serialized_end=1362
  _PLAYERLEFTGAME._serialized_start=1364
  _PLAYERLEFTGAME._serialized_end=1458
  _CLIENTDISCONNECTED._serialized_start=1460
  _CLIENTDISCONNECTED._serialized_end=1577
  _ASSIGNPLAYERSLOT._serialized_start=1579
  _ASSIGNPLAYERSLOT._serialized_end=1660
  _PLAYERALT._serialized_start=1662
  _PLAYERALT._serialized_end=1781
  _PLAYERALT_PLAYERNAMEALT._serialized_start=1725
  _PLAYERALT_PLAYERNAMEALT._serialized_end=1781
  _UUID._serialized_start=1783
  _UUID._serialized_end=1819
# @@protoc_insertion_point(module_scope)
