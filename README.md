# metalstats

Create a Topster-style canvas of your top Spotify music.

<img height="500" src="https://github.com/user-attachments/assets/37e7fbc3-63e1-4e98-8220-bede52bf8d40" />

## Environment Variables

To use the Spotify API, you **must set the following environment variables** before running the application (locally or in Docker):

| Variable                  | Description                  | Default Value                    |
|---------------------------|------------------------------|----------------------------------|
| `SPOTIFY_CLIENT_ID`       | Your Spotify client ID       |                                  |
| `SPOTIFY_CLIENT_SECRET`   | Your Spotify client secret   |                                  |
| `SPOTIFY_REDIRECT_URI`    | Your Spotify redirect uri    | `http://localhost:8000/callback` |
| `METALSTATS_DATA_DIR`     | Your data directory          | `data/`                          |

You can set these variables directly in your shell or via Docker as shown below.

## Running

```
git clone https://github.com/beucismis/metalstats
cd metalstats/
pip install .
uvicorn metalstats.main:app --reload
```

## Running with Docker

```
git clone https://github.com/beucismis/metalstats
cd metalstats/
docker build -t metalstats .
docker run -d \
  -p 8000:8000 \
  -e SPOTIFY_CLIENT_ID="spotify_client_id" \
  -e SPOTIFY_CLIENT_SECRET="spotify_client_secret" \
  -e SPOTIFY_REDIRECT_URI="spotify_redirect_uri" \
  --name metalstats \
  metalstats
```

## Usage

Once the service is running, you can access the API at `http://localhost:8000`.

## Developer Notes

- The ASGI app is defined as `app` in `src/metalstats/main.py`.
- When installed as a package, you can launch it using `uvicorn`, `hypercorn`, `fastapi-cli`, or any compatible ASGI tool.

## License

`metalstats` is distributed under the terms of the [MIT](LICENSE.txt) license.
