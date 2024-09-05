from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerDeviceClass, MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_STEP,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
    SUPPORT_SEEK,
    SUPPORT_CLEAR_PLAYLIST,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_REPEAT_SET,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PREVIOUS_TRACK,
    MEDIA_TYPE_ALBUM,
    MEDIA_TYPE_ARTIST,
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_EPISODE,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_PLAYLIST,
    MEDIA_TYPE_SEASON,
    MEDIA_TYPE_TRACK,
    MEDIA_TYPE_TVSHOW,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(entities, True)

class AppMediaPlayer(MediaPlayerEntity):

    def __init__(self):
        pass