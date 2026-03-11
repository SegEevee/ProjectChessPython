import sys
import os
from enum import Enum

existing_songs : dict[str,float] = { #music name : volume multiplier
    # Default pack
    "Calculated_Calm": 0.9,
    "Clockwork": 0.6,
    "Turnaround": 0.8,
    "Checkmate_Relief": 0.7,
    "Behind_The_Screen": 0.8,
    "Endgame_Time!" : 0.69, #nice
    "Music_To_Calculate_Like_Magnus" : 0.8,

    #hyper pack
    "Advanced_Pressure" : 0.8,
    "An_Outplayed_Opening" : 0.7,
    "Move_Of_The_Game" : 0.8,

    #retro pack
    #norhing yet

    #troll pack
    "19_Dollar_Fortnite_Card" : 1.0,
    "Another_Victory_For_The_OGs" : 1.0,
    "Copyright_Issues" : 1.0,
    "Fluffing_a_Duck" : 1.0,
    "Gandalf_Sax" : 1.0,
}



def get_asset_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # If not running as exe, use the normal folder
        print(f"Running in development mode.")
        return relative_path

    return os.path.join(base_path, relative_path)


class Music:
    def __init__(self, name, music_file,volume_multiplier=1.0):
        self.name = name
        self.music_file = music_file

def get_pack_from_name(pack_name) -> list[Music]:
    return_list = []
    pack_folder_path = get_asset_path(f"assets/sounds/board_music_packs/{pack_name}")
    pack_files = os.listdir(str(pack_folder_path)) #to make pycharm happy
    for music_file in pack_files:
        if music_file.endswith(".mp3") or music_file.endswith(".ogg"):
            music_name = music_file.rsplit(".", 1)[0]


            return_list.append(
                Music(
                    name= music_name,
                    music_file=get_asset_path(f"assets/board_music_packs/{pack_name}/{music_file}")
                )
            )

    return return_list

class MusicPack:
    def __init__(self, name):
        self.name = name
        self.tracks : list[Music] = get_pack_from_name(name)

MUSIC_PACK_NAMES = ["default"] #list of pack names, should match folder names in assets/board_music_packs


LOADED_PACKS = {}

class MediaPlayerState(Enum):
    PLAYING = 1
    PAUSED = 2
    OUTSIDE = 3
    SETTINGS = 4


class MusicManager:
    def __init__(self,mixer,starting_volume=0.5):
        self.media_player = mixer
        self.current_playlist = []
        self.last_requested_track = None
        self.state = MediaPlayerState.OUTSIDE
        self.volume = starting_volume

    def start_playlist(self):
        if not self.current_playlist:
            print("No tracks loaded in the playlist.")
            return

        self.state = MediaPlayerState.PLAYING
        self.load_music(self.current_playlist[0])
        self.media_player.music.play()

    def get_current_track(self):
        if self.state == MediaPlayerState.PLAYING:
            return self.last_requested_track
        return None

    def get_current_time(self):
        if self.state == MediaPlayerState.PLAYING or self.state == MediaPlayerState.PAUSED:
            return self.media_player.music.get_pos() / 1000.0
        return -1.0

    def set_current_time(self, time_seconds):
        if self.state == MediaPlayerState.PLAYING or self.state == MediaPlayerState.PAUSED:
            self.media_player.music.set_pos(time_seconds)
        else:
            print("Cannot set time when not playing or paused.")

    def load_music_pack(self, pack_name):
        if not pack_name in LOADED_PACKS:
            LOADED_PACKS[pack_name] = MusicPack(pack_name)

        music_pack = LOADED_PACKS[pack_name]

        for track in music_pack.tracks:
            self.current_playlist.append(track)
    def get_volume(self):
        return self.volume
    def get_true_volume(self):
        if not self.last_requested_track:
            return 0.0
        track_multiplier = existing_songs.get(self.last_requested_track.name, 1.0)
        return self.volume * track_multiplier

    def set_volume(self, volume):
        self.volume = volume #maybe they want 200% volume, who am I to judge

    def load_music(self, music: Music):
        self.last_requested_track = music
        self.media_player.music.load(music.music_file)

    def unpause_music(self):
        self.state = MediaPlayerState.PLAYING
        self.media_player.music.unpause()

    def pause_music(self):
        self.state = MediaPlayerState.PAUSED
        self.media_player.music.pause()

    def exit_music(self):
        self.state = MediaPlayerState.OUTSIDE
        self.media_player.music.stop()

if __name__ == "__main__":

    # Example usage
    playlist = get_pack_from_name("default")
    print(f"Loaded tracks: {[track.name for track in playlist]}")