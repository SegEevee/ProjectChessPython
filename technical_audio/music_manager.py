# <editor-fold desc="import..."
import sys
import os
import random
from mutagen.mp3 import MP3
from enum import Enum


sys.path.append(os.path.join(os.path.dirname(__file__), 'soloud'))
import soloud

# </editor-fold>

SONG_START_THRESHOLD = 3  # in seconds
END_SONG_THRESHOLD = 0.1  # in seconds

existing_songs: dict[str, float] = {
    # default pack
    "Calculated_Calm": 0.9,
    "Clockwork": 0.6,
    "Turnaround": 0.8,
    "Checkmate_Relief": 0.7,
    "Behind_The_Screen": 0.8,
    "Endgame_Time!": 0.69,
    "Endgame_Fantasy" : 0.8,
    "Music_To_Calculate_Like_Magnus": 0.8,
    "A_Pawn's_Dream" : 0.9,

    # hyper pack
    "Advanced_Pressure": 0.8,
    "An_Outplayed_Opening": 0.7,
    "Move_Of_The_Game": 0.8,
    "Gearing_Mind": 0.7,
    "Binary_Gambit": 0.7,

    # retro pack
    "Thoughts_In_8-Bit":0.7,


    # troll pack
    "19_Dollar_Fortnite_Card": 1.0,
    "Another_Victory_For_The_OGs": 1.0,
    "Copyright_Issues": 1.0,
    "Fluffing_a_Duck": 1.0,
    "Gandalf_Sax": 1.0,
}


def get_asset_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class Music:
    def __init__(self, name, music_file, volume_multiplier=1.0):
        self.name = name
        self.music_file = music_file
        self.length = MP3(music_file).info.length
        self.volume_multiplier = volume_multiplier


def get_pack_from_name(pack_name) -> list[Music]:
    return_list = []
    pack_folder_path = get_asset_path(f"assets/sounds/board_music_packs/{pack_name}")
    if not os.path.exists(pack_folder_path):
        print(f"WARNING: Pack folder not found at {pack_folder_path}")
        return return_list

    pack_files = os.listdir(str(pack_folder_path))
    for music_file in pack_files:
        if music_file.endswith(".mp3") or music_file.endswith(".ogg"):
            music_name = music_file.rsplit(".", 1)[0]
            return_list.append(
                Music(
                    name=music_name,
                    music_file=get_asset_path(f"assets/sounds/board_music_packs/{pack_name}/{music_file}"),
                    volume_multiplier=existing_songs.get(music_name, 1.0)
                )
            )
    return return_list


class MusicPack:
    def __init__(self, name):
        self.name = name
        self.tracks: list[Music] = get_pack_from_name(name)


MUSIC_PACK_NAMES = ["default_pack", "hyper_pack", "trolls_pack","retro_pack"]
LOADED_PACKS = {}


class MediaPlayerState(Enum):
    PLAYING = 1
    PAUSED = 2
    OUTSIDE = 3
    SETTINGS = 4


class MusicManager:
    # Notice we removed the pygame_module argument! We don't need it.
    def __init__(self, user_preferences):
        self.user_preferences = user_preferences
        self.volume = user_preferences.get("volume", 0.5)

        # --- SOLOUD SETUP ---
        self.sl = soloud.Soloud()
        self.sl.init()

        # The CD Player (Streams large files from the hard drive)
        self.audio_source = soloud.WavStream()

        # The Leash (How we talk to the specific song playing right now)
        self.current_voice_handle = None

        # --- THE MUFFLE FILTER (Low-pass) ---
        self.muffle_filter = soloud.BiquadResonantFilter()
        # Cut off high frequencies (makes it sound underwater or behind a door)
        self.muffle_filter.set_params(soloud.BiquadResonantFilter.LOWPASS, 1000, 2)
        # Attach the filter to our CD player. (It starts at 0% strength)
        self.audio_source.set_filter(0, self.muffle_filter)

        self.current_playlist = []
        self.last_requested_track: Music | None = None
        self.current_track_index = 0
        self.state = MediaPlayerState.OUTSIDE
        self.board_music_timestamp = 0.0

        self.is_muffled = False

    def clear_playlist(self):
        self.current_playlist.clear()
        self.current_track_index = 0
        self.exit_music()
        self.board_music_timestamp = 0.0

    def add_pack(self, pack_name):
        if pack_name not in LOADED_PACKS:
            self.load_music_pack(pack_name)

        pack = LOADED_PACKS[pack_name]
        was_empty = len(self.current_playlist) == 0

        for track in pack.tracks:
            self.current_playlist.append(track)

        if was_empty and (self.state == MediaPlayerState.PLAYING or self.state == MediaPlayerState.PAUSED):
            self.start_playlist()

    def add_track_last(self, track: Music):
        was_empty = len(self.current_playlist) == 0
        self.current_playlist.append(track)
        if was_empty and (self.state == MediaPlayerState.PLAYING or self.state == MediaPlayerState.PAUSED):
            self.start_playlist()

    def add_track_next(self, track: Music):
        if not self.current_playlist:
            self.current_playlist.append(track)
        else:
            self.current_playlist.insert(self.current_track_index + 1, track)

    def start_playlist(self):
        if not self.current_playlist: return
        self.state = MediaPlayerState.PLAYING
        self.current_track_index = 0
        self.load_music(self.current_playlist[self.current_track_index])
        self.play_song()

    def continue_playlist(self):
        if not self.current_playlist: return
        self.state = MediaPlayerState.PLAYING
        self.load_music(self.current_playlist[self.current_track_index])
        print("Continuing playlist")
        self.play_song(continue_song=True)

    def next_track(self):
        if not self.current_playlist: return
        self.current_track_index = (self.current_track_index + 1) % len(self.current_playlist)
        self.load_music(self.current_playlist[self.current_track_index])
        print("Next track")
        self.play_song()

    def prev_track(self):
        if not self.current_playlist: return
        self.current_track_index = (self.current_track_index - 1) % len(self.current_playlist)
        self.load_music(self.current_playlist[self.current_track_index])
        print("Previous track")
        self.play_song()

    def load_music(self, music: Music):
        self.last_requested_track = music
        # We slide the MP3/OGG file into the CD Player
        self.audio_source.load(music.music_file)

    def get_current_track(self):
        if self.state in [MediaPlayerState.PLAYING, MediaPlayerState.PAUSED]:
            return self.last_requested_track
        return None

    def get_volume(self):
        return self.volume

    def get_true_volume(self):
        if not self.last_requested_track: return 0.0
        return self.volume * self.last_requested_track.volume_multiplier

    def set_volume(self, volume):
        self.volume = volume
        if self.state == MediaPlayerState.PLAYING and self.current_voice_handle is not None:
            self.sl.set_volume(self.current_voice_handle, self.get_true_volume())

    def load_music_pack(self, pack_name):
        if pack_name not in LOADED_PACKS:
            LOADED_PACKS[pack_name] = MusicPack(pack_name)

    def play_song(self, continue_song=False):
        self.state = MediaPlayerState.PLAYING
        if not self.does_user_allow(): return

        # STOP the old song before starting the new one to prevent overlap
        if self.current_voice_handle is not None:
            self.sl.stop(self.current_voice_handle)

        print("played, curr timestamp =", self.board_music_timestamp)

        # Hit play! SoLoud hands us the Leash (handle) to control it
        self.current_voice_handle = self.sl.play(self.audio_source)
        self.sl.set_volume(self.current_voice_handle, self.get_true_volume())

        wet_strength = 1.0 if self.is_muffled else 0.0
        self.sl.set_filter_parameter(self.current_voice_handle, 0, 0, wet_strength)

        if continue_song and self.board_music_timestamp >= SONG_START_THRESHOLD:
            # SoLoud's time travel actually works instantly!
            self.set_timestamp_seconds(self.board_music_timestamp)
        else:
            self.board_music_timestamp = 0.0

    def unpause_music(self):
        self.state = MediaPlayerState.PLAYING
        if self.current_voice_handle is not None:
            self.sl.set_pause(self.current_voice_handle, False)

    def pause_music(self):
        self.state = MediaPlayerState.PAUSED
        if self.current_voice_handle is not None:
            self.sl.set_pause(self.current_voice_handle, True)

    def get_timestamp_seconds(self):
        # BOUNCER: Don't ask for the time if the leash is dead
        if self.current_voice_handle is None or not self.sl.is_valid_voice_handle(self.current_voice_handle):
            return 0.0

        # THE FIX: Read the actual audio tape, NOT the stopwatch!
        return self.sl.get_stream_position(self.current_voice_handle)

    def set_timestamp_seconds(self, timestamp):
        # BOUNCER: Only seek if the song is actively playing or paused
        if self.current_voice_handle is not None and self.sl.is_valid_voice_handle(self.current_voice_handle):
            # Clamp the math to prevent seeking past the end
            safe_time = max(0.0, min(timestamp, self.last_requested_track.length - 0.2))

            # --- THE CORE FIX: The Sledgehammer ---
            # The MP3 decoder panics and falls back to old cache when seeked repeatedly.
            # We must kill the voice and restart it to force a completely clean read head!
            was_paused = self.state == MediaPlayerState.PAUSED

            # 1. Execute the voice
            self.sl.stop(self.current_voice_handle)

            # 2. Spawn a brand new voice from the source
            self.current_voice_handle = self.sl.play(self.audio_source)
            self.sl.set_volume(self.current_voice_handle, self.get_true_volume())

            wet_strength = 1.0 if self.is_muffled else 0.0
            self.sl.set_filter_parameter(self.current_voice_handle, 0, 0, wet_strength)

            # 3. Time travel on the fresh instance
            self.sl.seek(self.current_voice_handle, safe_time)

            # 4. Put it back to sleep if the user had it paused
            if was_paused:
                self.sl.set_pause(self.current_voice_handle, True)

    def finished_song(self):
        if self.state != MediaPlayerState.PLAYING:
            return False
        return self.get_timestamp_seconds() >= self.last_requested_track.length - END_SONG_THRESHOLD

    def does_user_allow(self):
        return not self.user_preferences.get("master_mute", False) and not self.user_preferences.get("music_mute",
                                                                                                     False)

    def exit_music(self):
        self.board_music_timestamp = self.get_timestamp_seconds()
        self.state = MediaPlayerState.OUTSIDE
        if self.current_voice_handle is not None:
            self.sl.stop(self.current_voice_handle)

    # ==========================================
    # NEW DJ CONTROLS (Live DSP Effects)
    # ==========================================

    def set_muffle(self, enabled: bool):
        """Creates the 'listening through a wall' effect."""
        self.is_muffled = enabled

        if self.current_voice_handle is not None:
            # 0 = Which filter? (We only attached 1)
            # 0 = Which attribute? (0 is the "Wet" attribute, meaning how strong it is)
            # Value = 1.0 is full muffle, 0.0 is completely off
            wet_strength = 1.0 if enabled else 0.0
            self.sl.set_filter_parameter(self.current_voice_handle, 0, 0, wet_strength)

    def set_playback_speed(self, speed_multiplier: float):
        """
        Changes pitch and tempo simultaneously (like a vinyl record).
        0.5 = Half speed (Deep voice)
        1.0 = Normal
        2.0 = Double speed (Chipmunk)
        """
        if self.current_voice_handle is not None:
            self.sl.set_relative_play_speed(self.current_voice_handle, speed_multiplier)

    def is_playlist_empty(self):
        return not self.current_playlist

    def shuffle_playlist(self):
        random.shuffle(self.current_playlist)

    def cleanup(self):
        """Crucial: When the game closes, we must turn off the engine to free memory."""
        self.sl.deinit()
