import os
import sys
import json

APP_ID = 'rkisearch'

DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 5200,
    "slug": f"/{APP_ID}",
    f"{APP_ID}_home": f"/tmp/{APP_ID}-data",
}

DEFAULT_USERS = { "demo" : { 'password': "swordfish" , 'role': "theman" } }


def ensure(what, default, fill=False):
    for p in f'{what}.json', f'$XDG_CONFIG_HOME/{APP_ID}/{what}.json', f'$HOME/.config/{APP_ID}/{what}.json':
        p = os.path.abspath(os.path.expandvars(p))
        if os.path.exists(p):
            try:
                with open(p, "rt") as f:
                    c = json.loads(f.read())
                    if fill:
                        for key in default:
                            if key not in c:
                                c[key] = DEFAULT_CONFIG[key]
                    return p, c
            except Exception as e:
                print(f'Error loading /parsing {p}: {e}', file=sys.stderr)
                sys.exit(1)
            break
    else:
        # create default config
        if os.environ.get('XDG_CONFIG_HOME', None):
            p = f'$XDG_CONFIG_HOME/{APP_ID}/{what}.json'
        elif os.environ.get('HOME', None):
            p = f'$HOME/.config/{APP_ID}/{what}.json'
        else:
            print("Don't know where to create config!", file=sys.stderr)
            sys.exit(1)

        p = os.path.abspath(os.path.expandvars(p))
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wt") as f:
                ret = default
                json.dump(ret, f)
            print(f'Config created at {p}', file=sys.stderr)
            return p, ret
        except Exception as e:
            print(f'Error creating / parsing {p}: {e}', file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    # we're called by the launcher who wants to know our IP and port
    _, config = ensure('config', DEFAULT_CONFIG, fill=True)
    host = config.get('host', DEFAULT_CONFIG['host'])
    port = config.get('port', DEFAULT_CONFIG['port'])
    app_home = config.get(f'{APP_ID}_home', DEFAULT_CONFIG[f'{APP_ID}_home'])
    print(f'{host}:{port};{app_home}/logs')
