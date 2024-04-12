"""
 * Copyright (C) 2024 VioletXF, khoeun03
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import hashlib
import random
import re
from collections import OrderedDict
import os
from typing import Union
LaneAutoplay = 1
SectionRate = 2
BpmChange = 3
BgaPlay = 4
PoorPlay = 6
LayerPlay = 7
BpmChangeExtend = 8
Stop = 9

P1KeyBase = 1 * 36 + 1
P2KeyBase = 2 * 36 + 1
P1InvisibleKeyBase = 3 * 36 + 1
P2InvisibleKeyBase = 4 * 36 + 1
P1LongKeyBase = 5 * 36 + 1
P2LongKeyBase = 6 * 36 + 1
P1MineKeyBase = 13 * 36 + 1
P2MineKeyBase = 14 * 36 + 1

Scroll = 1020

Beat7 = [0, 1, 2, 3, 4, 7, -1, 5, 6, 8, 9, 10, 11, 12, 15, -1, 13, 14]

class Note:
    def __init__(self, wav: int):
        self.lane = 0
        self.wav = wav
        self.timeline: Union[TimeLine, None] = None
        self.is_played = False
        self.is_dead = False
        self.played_time = 0
    def is_long_note(self):
        return False
    def is_landmine_note(self):
        return False
    def play(self, time: int):
        self.is_played = True
        self.played_time = time
    def press(self, time: int):
        self.play(time)
    def reset(self):
        self.is_played = False
        self.is_dead = False
        self.played_time = 0
class LandmineNote(Note):
    def __init__(self, damage: float):
        self.lane = -1
        self.timeline = None
        self.damage = damage
    def is_long_note(self):
        return False
    def is_landmine_note(self):
        return True
class LongNote(Note):
    def __init__(self, wav: int):
        super().__init__(wav)
        self.tail: Union[LongNote, None] = None
        self.head: Union[LongNote, None] = None
        self.is_holding = False
        self.release_time = 0
    def is_long_note(self):
        return True
    def is_landmine_note(self):
        return False
    def is_tail(self):
        return self.tail is None
    def press(self, time: int):
        self.play(time)
        self.is_holding = True
        if self.tail is not None:
            self.tail.is_holding = True
    def release(self, time: int):
        self.play(time)
        self.is_holding = False
        if self.head is not None:
            self.head.is_holding = False
        self.release_time = time
    def reset(self):
        super().reset()
        self.is_holding = False
        self.release_time = 0
class TimeLine:
    def __init__(self):
        self.background_notes: list[Note] = []
        self.invisible_notes: list[Union[Note, None]] = [None for _ in range(16)]
        self.notes: list[Union[Note, None]] = [None for _ in range(16)]
        self.landmine_notes: list[Union[LandmineNote, None]] = [None for _ in range(16)]
        self.bpm = 0.0
        self.bpm_change = False
        self.bpm_change_applied = False
        self.bga_base = -1
        self.bga_layer = -1
        self.bga_poor = -1
        self.stop_length = 0.0
        self.scroll = 1.0
        self.timing = 0
    def set_note(self, lane: int, note: Note):
        self.notes[lane] = note
        note.lane = lane
        note.timeline = self
        return self
    def set_invisible_note(self, lane: int, note: Note):
        self.invisible_notes[lane] = note
        note.lane = lane
        note.timeline = self
        return self
    def set_landmine_note(self, lane: int, note: LandmineNote):
        self.landmine_notes[lane] = note
        note.lane = lane
        note.timeline = self
        return self
    def add_background_note(self, note: Note):
        self.background_notes.append(note)
        note.timeline = self
        return self
    def get_stop_duration(self):
        return 1250000.0 * self.stop_length / self.bpm
class Measure:
    def __init__(self):
        self.scale = 1.0
        self.timing = 0
        self.timelines: list[TimeLine] = []

class ChartMeta:
    def __init__(self):
        self.sha256 = ""
        self.md5 = ""
        self.bms_path = ""
        self.folder = ""
        self.artist = ""
        self.subartist = ""
        self.bpm = 0.0
        self.genre = ""
        self.title = ""
        self.subtitle = ""
        self.rank = 1
        self.total = 100.0
        self.play_length = 0
        self.total_length = 0
        self.banner = ""
        self.stage_file = ""
        self.backbmp = ""
        self.preview = ""
        self.bga_poor_default = False
        self.difficulty = 0
        self.play_level = 3
        self.min_bpm = 0.0
        self.max_bpm = 0.0
        self.player = 1
        self.key_mode = 5
        self.is_dp = False
        self.total_notes = 0
        self.total_long_notes = 0
        self.total_scratch_notes = 0
        self.total_backspin_notes = 0
        self.lnmode = 0
    def get_key_lane_count(self):
        return self.key_mode
    def get_scratch_lane_count(self):
        return 2 if self.is_dp else 1
    def get_total_lane_count(self):
        return self.get_key_lane_count() + self.get_scratch_lane_count()
    def get_key_lane_indices(self):
        if self.key_mode == 5:
            return [0,1,2,3,4]
        elif self.key_mode == 7:
            return [0,1,2,3,4,5,6]
        elif self.key_mode == 10:
            return [0,1,2,3,4,8,9,10,11,12]
        elif self.key_mode == 14:
            return [0,1,2,3,4,5,6,8,9,10,11,12,13,14]
        else:
            return []
    def get_scratch_lane_indices(self):
        if self.is_dp:
            return [7,15]
        else:
            return [7]
    def get_total_lane_indices(self):
        return self.get_key_lane_indices() + self.get_scratch_lane_indices()
    def __str__(self):
        return f"""
        SHA256: {self.sha256}
        MD5: {self.md5}
        Title: {self.title}
        Subtitle: {self.subtitle}
        Artist: {self.artist}
        Subartist: {self.subartist}
        Genre: {self.genre}
        Difficulty: {self.difficulty}
        BPM: {self.bpm}
        Rank: {self.rank}
        Total: {self.total}
        Player: {self.player}
        Key Mode: {self.key_mode}
        Is DP: {self.is_dp}
        Total Notes: {self.total_notes}
        Total Long Notes: {self.total_long_notes}
        Total Scratch Notes: {self.total_scratch_notes}
        Total Backspin Notes: {self.total_backspin_notes}
        LN Mode: {self.lnmode}
        """
class Chart:
    def __init__(self):
        self.meta = ChartMeta()
        self.measures: list[Measure] = []
        self.wav_table: dict[int, str] = {}
        self.bmp_table: dict[int, str] = {}
    def __str__(self):
        return f"Chart: {self.meta.title} Meta: {self.meta}"
    def __repr__(self):
        return self.__str__()
class BmsParser:
    no_wav = -1
    def __init__(self, path):
        self.path = path
        self.use_base62 = False
        self.chart = Chart()
        self.chart.meta.folder = os.path.dirname(path)
        self.bpm_table: dict[int, float] = {}
        self.stop_length_table: dict[int, float] = {}
        self.lnobj = -1
        self.lntype = -1
        self.scroll_table: dict[int, float] = {}
    def parse_int(self, s: str, force_base36: bool = False):
        if force_base36 or not self.use_base62:
            return int(s, 36)
        result = 0
        for c in s:
            result *= 62
            if '0' <= c <= '9':
                result += ord(c) - ord('0')
            elif 'A' <= c <= 'Z':
                result += ord(c) - ord('A') + 10
            elif 'a' <= c <= 'z':
                result += ord(c) - ord('a') + 36
            else:
                raise ValueError(f"Invalid character {c}")
        return result
    def match_header(self, line: str, header: str):
        return line.upper().startswith(header)
    def parse_header(self, cmd: str, xx: str, value: str):
        if self.match_header(cmd, "BASE"):
            if len(value) == 0: return
            if value == "62":
                self.use_base62 = True
            else:
                self.use_base62 = False
        elif self.match_header(cmd, "PLAYER"):
            self.chart.meta.player = int(value)
        elif self.match_header(cmd, "GENRE"):
            self.chart.meta.genre = value
        elif self.match_header(cmd, "TITLE"):
            self.chart.meta.title = value
        elif self.match_header(cmd, "SUBTITLE"):
            self.chart.meta.subtitle = value
        elif self.match_header(cmd, "ARTIST"):
            self.chart.meta.artist = value
        elif self.match_header(cmd, "SUBARTIST"):
            self.chart.meta.subartist = value
        elif self.match_header(cmd, "DIFFICULTY"):
            self.chart.meta.difficulty = int(value)
        elif self.match_header(cmd, "BPM"):
            if len(value) == 0: return
            if len(xx) == 0:
                self.chart.meta.bpm = float(value)
            else:
                id = self.parse_int(xx)
                self.bpm_table[id] = float(value)
        elif self.match_header(cmd, "STOP"):
            if len(value) == 0 or len(xx) == 0: return
            id = self.parse_int(xx)
            self.stop_length_table[id] = float(value)
        elif self.match_header(cmd, "PLAYLEVEL"):
            self.chart.meta.play_level = int(value)
        elif self.match_header(cmd, "RANK"):
            self.chart.meta.rank = int(value)
        elif self.match_header(cmd, "TOTAL"):
            total = float(value)
            if total > 0:
                self.chart.meta.total = total
        elif self.match_header(cmd, "STAGEFILE"):
            self.chart.meta.stage_file = value
        elif self.match_header(cmd, "BANNER"):
            self.chart.meta.banner = value
        elif self.match_header(cmd, "BACKBMP"):
            self.chart.meta.backbmp = value
        elif self.match_header(cmd, "PREVIEW"):
            self.chart.meta.preview = value
        elif self.match_header(cmd, "WAV"):
            if len(value) == 0 or len(xx) == 0: return
            id = self.parse_int(xx)
            self.chart.wav_table[id] = value
        elif self.match_header(cmd, "BMP"):
            if len(value) == 0 or len(xx) == 0: return
            id = self.parse_int(xx)
            self.chart.bmp_table[id] = value
            if xx == "00":
                self.chart.meta.bga_poor_default = True
        elif self.match_header(cmd, "LNOBJ"):
            self.lnobj = self.parse_int(value)
        elif self.match_header(cmd, "LNTYPE"):
            self.lntype = int(value)
        elif self.match_header(cmd, "LNMODE"):
            self.chart.meta.lnmode = int(value)
        elif self.match_header(cmd, "SCROLL"):
            id = self.parse_int(xx)
            self.scroll_table[id] = float(value)
        else:
            print(f"Unknown header: {cmd}")
    def gcd(self, a: int, b: int):
        while b != 0:
            a, b = b, a % b
        return a
    def to_wave_id(self, wav: str):
        if len(wav) == 0: return self.no_wav
        decoded = self.parse_int(wav)
        if decoded in self.chart.wav_table:
            return decoded
        return self.no_wav
    def parse(self):
        # calculate sha256 hash
        # read file
        bytes = open(self.path, 'rb').read()
        # calculate hash
        
        self.chart.meta.sha256 = hashlib.sha256(bytes).hexdigest()
        self.chart.meta.md5 = hashlib.md5(bytes).hexdigest()
        headerRegex = r"^#([A-Za-z]+?)(\\d\\d)? +?(.+)?"
        last_measure = -1
        measures: dict[int, list[tuple[int, str]]] = {}
        content = bytes.decode('shift-jis')
        random_stack: list[int] = []
        skip_stack: list[bool] = []
        prng = random.Random()
        # read line by line, accept both crlf and lf
        for line in content.split("\n"):
            if line.endswith("\r"):
                line = line[:-1]
            if self.match_header(line, "#IF"):
                if len(random_stack) == 0: continue
                current_random = random_stack[-1]
                n = int(line[4:])
                skip_stack.append(current_random != n)
                continue
            if self.match_header(line, "#ELSE"):
                if len(skip_stack) == 0: continue
                current_skip = skip_stack[-1]
                skip_stack.pop()
                skip_stack.append(not current_skip)
                continue
            if self.match_header(line, "#ELSEIF"):
                if len(skip_stack) == 0: continue
                current_skip = skip_stack[-1]
                n = int(line[8:])
                skip_stack.pop()
                skip_stack.append(current_skip and current_skip != n)
                continue
            if self.match_header(line, "#ENDIF") or self.match_header(line, "#END IF"):
                if len(skip_stack) == 0: continue
                skip_stack.pop()
                continue
            if self.match_header(line, "#RANDOM") or self.match_header(line, "#RONDAM"):
                n = int(line[7:])
                random_stack.append(prng.randint(1, n))
                continue
            if self.match_header(line, "#ENDRANDOM"):
                if len(random_stack) == 0: continue
                random_stack.pop()
                continue
            if len(line) >= 7 and line[1].isdigit() and line[2].isdigit() and line[3].isdigit() and line[6] == ":":
                measure = int(line[1:4])
                last_measure = max(last_measure, measure)
                if measure not in measures:
                    measures[measure] = []
                channel = self.parse_int(line[4:6])
                measures[measure].append((channel, line[7:]))
            else:
                if self.match_header(line, "#WAV"):
                    if len(line) < 7: continue
                    xx = line[4:6]
                    value = line[7:]
                    self.parse_header("WAV", xx, value)
                elif self.match_header(line, "#BMP"):
                    if len(line) < 7: continue
                    xx = line[4:6]
                    value = line[7:]
                    self.parse_header("BMP", xx, value)
                elif self.match_header(line, "#BPM"):
                    if line[4:].startswith(" "):
                        value = line[5:]
                        self.parse_header("BPM", "", value)
                    else:
                        if len(line) < 7: continue
                        xx = line[4:6]
                        value = line[7:]
                        self.parse_header("BPM", xx, value)
                elif self.match_header(line, "#STOP"):
                    if len(line) < 8: continue
                    xx = line[5:7]
                    value = line[8:]
                    self.parse_header("STOP", xx, value)
                elif self.match_header(line, "#SCROLL"):
                    if len(line) < 10: continue
                    xx = line[7:9]
                    value = line[10:]
                    self.parse_header("SCROLL", xx, value)
                else:
                    match = re.match(headerRegex, line)
                    if match:
                        cmd = match.group(1)
                        xx = match.group(2)
                        value = match.group(3)
                        if value == None or len(value) == 0:
                            value = xx
                            xx = ""
                        self.parse_header(cmd, xx, value)
        time_passed = 0.0
        total_notes = 0
        total_long_notes = 0
        total_scratch_notes = 0
        total_backspin_notes = 0
        total_landmine_notes = 0
        current_bpm = self.chart.meta.bpm
        min_bpm = self.chart.meta.bpm
        max_bpm = self.chart.meta.bpm
        last_note: list[Union[Note, None]] = [None] * 16
        ln_start: list[Union[LongNote, None]] = [None] * 16
        for i in range(last_measure+1):
            if i not in measures:
                measures[i] = []
            measure = Measure()
            timelines: OrderedDict[float, TimeLine] = OrderedDict()
            for channel, data in measures[i]:
                if channel == SectionRate:
                    measure.scale = float(data)
                    continue
                lane_number = 0
                if channel >= P1KeyBase and channel < P1KeyBase + 9:
                    lane_number = Beat7[channel - P1KeyBase]
                    channel = P1KeyBase
                elif channel >= P2KeyBase and channel < P2KeyBase + 9:
                    lane_number = Beat7[channel - P2KeyBase + 9]
                    channel = P1KeyBase
                elif channel >= P1InvisibleKeyBase and channel < P1InvisibleKeyBase + 9:
                    lane_number = Beat7[channel - P1InvisibleKeyBase]
                    channel = P1InvisibleKeyBase
                elif channel >= P2InvisibleKeyBase and channel < P2InvisibleKeyBase + 9:
                    lane_number = Beat7[channel - P2InvisibleKeyBase + 9]
                    channel = P1InvisibleKeyBase
                elif channel >= P1LongKeyBase and channel < P1LongKeyBase + 9:
                    lane_number = Beat7[channel - P1LongKeyBase]
                    channel = P1LongKeyBase
                elif channel >= P2LongKeyBase and channel < P2LongKeyBase + 9:
                    lane_number = Beat7[channel - P2LongKeyBase + 9]
                    channel = P1LongKeyBase
                elif channel >= P1MineKeyBase and channel < P1MineKeyBase + 9:
                    lane_number = Beat7[channel - P1MineKeyBase]
                    channel = P1MineKeyBase
                elif channel >= P2MineKeyBase and channel < P2MineKeyBase + 9:
                    lane_number = Beat7[channel - P2MineKeyBase + 9]
                    channel = P1MineKeyBase
                if lane_number == -1:
                    continue
                is_scratch = lane_number == 7 or lane_number == 15
                if lane_number == 5 or lane_number == 6 or lane_number == 13 or lane_number == 14:
                    if self.chart.meta.key_mode == 5:
                        self.chart.meta.key_mode = 7
                    elif self.chart.meta.key_mode == 10:
                        self.chart.meta.key_mode = 14
                if lane_number >= 8:
                    if self.chart.meta.key_mode == 7:
                        self.chart.meta.key_mode = 14
                    elif self.chart.meta.key_mode == 5:
                        self.chart.meta.key_mode = 10
                    self.chart.meta.is_dp = True
                data_count = len(data) // 2
                for j in range(data_count):
                    val = data[j*2:j*2+2]
                    if val == "00":
                        if len(timelines) == 0 and j == 0:
                            timelines[0] = TimeLine() # ghost timeline
                        continue
                    g = self.gcd(j, data_count)
                    position = (j // g) / (data_count // g)

                    if position not in timelines:
                        timelines[position] = TimeLine()
                    timeline = timelines[position]

                    if channel == LaneAutoplay:
                        if self.parse_int(val) != 0:
                            bg_note = Note(self.to_wave_id(val))
                            timeline.add_background_note(bg_note)
                    elif channel == BpmChange:
                        # hex to int
                        bpm = int(val, 16)
                        timeline.bpm = bpm
                        timeline.bpm_change = True
                    elif channel == BgaPlay:
                        timeline.bga_base = self.parse_int(val)
                    elif channel == PoorPlay:
                        timeline.bga_poor = self.parse_int(val)
                    elif channel == LayerPlay:
                        timeline.bga_layer = self.parse_int(val)
                    elif channel == BpmChangeExtend:
                        id = self.parse_int(val)
                        if id in self.bpm_table:
                            timeline.bpm = self.bpm_table[id]
                        else:
                            timeline.bpm = 0.0
                        timeline.bpm_change = True
                    elif channel == Scroll:
                        id = self.parse_int(val)
                        if id in self.scroll_table:
                            timeline.scroll = self.scroll_table[id]
                        else:
                            timeline.scroll = 1.0
                    elif channel == Stop:
                        id = self.parse_int(val)
                        if id in self.stop_length_table:
                            timeline.stop_length = self.stop_length_table[id]
                        else:
                            timeline.stop_length = 0.0
                    elif channel == P1KeyBase:
                        ch = self.parse_int(val)
                        if ch == self.lnobj and last_note[lane_number] is not None:
                            if is_scratch:
                                total_scratch_notes += 1
                            else:
                                total_long_notes += 1
                            last = last_note[lane_number]
                            last_note[lane_number] = None
                            assert last is not None
                            last_timeline = last.timeline
                            assert last_timeline is not None
                            ln = LongNote(last.wav)
                            del last
                            ln.tail = LongNote(self.no_wav)
                            ln.tail.head = ln
                            last_timeline.set_note(lane_number, ln)
                            timeline.set_note(lane_number, ln.tail)
                        else:
                            note = Note(self.to_wave_id(val))
                            last_note[lane_number] = note
                            total_notes += 1
                            if is_scratch:
                                total_scratch_notes += 1
                            timeline.set_note(lane_number, note)
                    elif channel == P1InvisibleKeyBase:
                        invisible_note = Note(self.to_wave_id(val))
                        timeline.set_invisible_note(lane_number, invisible_note)
                    elif channel == P1LongKeyBase:
                        if self.lntype == 1:
                            if ln_start[lane_number] is None:
                                total_notes += 1
                                if is_scratch:
                                    total_scratch_notes += 1
                                else:
                                    total_long_notes += 1
                                
                                ln = LongNote(self.to_wave_id(val))
                                ln_start[lane_number] = ln
                                timeline.set_note(lane_number, ln)
                            else:
                                tail = LongNote(self.no_wav)
                                tail.head = ln_start[lane_number]
                                assert tail.head is not None
                                tail.head.tail = tail
                                timeline.set_note(lane_number, tail)
                                ln_start[lane_number] = None
                    elif channel == P1MineKeyBase:
                        total_landmine_notes += 1
                        damage = self.parse_int(val, True) / 2.0
                        timeline.set_note(lane_number, LandmineNote(damage))
            self.chart.meta.total_notes = total_notes
            self.chart.meta.total_long_notes = total_long_notes
            self.chart.meta.total_scratch_notes = total_scratch_notes
            self.chart.meta.total_backspin_notes = total_backspin_notes

            last_position = 0.0
            measure.timing = int(time_passed)
            for position, timeline in sorted(timelines.items()):
                interval = 240000000.0 * (position - last_position) * measure.scale / current_bpm
                time_passed += interval
                timeline.timing = int(time_passed)
                if timeline.bpm_change:
                    current_bpm = timeline.bpm
                    min_bpm = min(min_bpm, current_bpm)
                    max_bpm = max(max_bpm, current_bpm)
                else:
                    timeline.bpm = current_bpm
                time_passed += timeline.get_stop_duration()
                measure.timelines.append(timeline)
                last_position = position
            if len(measure.timelines) == 0:
                timeline = TimeLine()
                timeline.timing = int(time_passed)
                timeline.bpm = current_bpm
                measure.timelines.append(timeline)
            self.chart.meta.play_length = int(time_passed)
            time_passed += 240000000.0 * (1 - last_position) * measure.scale / current_bpm
            self.chart.measures.append(measure)
        self.chart.meta.total_length = int(time_passed)
        self.chart.meta.min_bpm = min_bpm
        self.chart.meta.max_bpm = max_bpm
        return self.chart
