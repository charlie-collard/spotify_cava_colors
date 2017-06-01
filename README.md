# Spotify Cava Colors

Attempt to choose suitable colors for Cava to match the current song on Spotify

## Installation

Place your spotify app credentials in the `auth/app_credentials` file and
a refresh token with the `user-read-currently-playing` and/or
`user-read-playback-state` scope in the `auth/refresh_token` file.

Then:
```
pip install -r requirements.txt
ln -rs spotify_cava_colors.py ~/bin/spotify_cava_colors
spotify_cava_colors
```

## Info

The script will first make a request to the Spotify API, asking for the user's
currently playing song. It will then download the album art for that song,
decompose it into several characteristic colors, choose the "best" two colors,
write those colors into the cava config, then tell cava to reload.

The script will NOT automatically run when Spotify changes track, but one way
of doing this might be to listen for notifications and run the script every
time a Spotify notification is detected. An example bash script is included.

It is assumed your cava config is stored at `~/.config/cava/config`, and that
you have uncommented the relevant lines for gradient colors.
