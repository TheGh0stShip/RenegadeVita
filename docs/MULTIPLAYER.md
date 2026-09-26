# Experimental Multiplayer

Dev195's native ARM executable joined RenCorner in Vita3K. This is a development
checkpoint, not a complete TT client, a W3DHub launcher port, or physical Vita
acceptance. Original WWNet, Commando, Combat, and archive owners remain in use.
See [evidence and limitations](../reports/DEV195_RENCORNER_NATIVE_JOIN.md).

## Requirements

- The [full-port VPK and complete retail data](INSTALLING.md), not the tutorial subset.
- Internet access and storage for the server's required packages. The tested
  City_U1 session downloaded five packages totalling approximately 320 MB;
  other maps and server revisions can require different packages and space.
- A valid privately provisioned retail identity, and a trusted PEM CA bundle.
  Neither is supplied with the VPK. Do not share serials or generated identities.

## Private Setup

Run the local helper; it prompts without echoing the retail serial:

```sh
python3 tools/configure_client_identity.py --output /private/path/tt-identity-v1.txt
```

Place that file and a current trusted PEM CA bundle named `cacert.pem` under
`ux0:data/renegade/user/config/`. TLS certificate and hostname verification stay
enabled. On Linux, the maintained system bundle is commonly
`/etc/ssl/certs/ca-certificates.crt`; obtain it from your trusted OS installation,
not an unknown download. Keep identity files out of screenshots, logs and Git.

Back up any existing title installation and user settings before installing a
development candidate. Do not overwrite saves or the retail data tree.

## One-Shot Direct Entry

For the verified RenCorner target, create
`ux0:data/renegade/user/config/direct-ip-launch-v1.txt` containing this line,
including a final newline:

```text
tt://51.222.10.72:5001
```

Launch the title. The request is consumed; later launches without a request use
the ordinary frontend. The experimental client requests the name `PS Vita`.
The observed public server list displayed `PSVita`; exact-name handling is not
yet established. This is direct IP, not dependence on the retired GameSpy service.

The server selects its current map. Packages download into
`ux0:data/renegade/cache/ttfs/`, are validated, then mounted through original
archive factories. Do not copy downloaded server assets into the source tree,
release package, or retail installation. Do not redistribute them.

## Current Limits

Dev195 verified joining, rendering, bounded movement and clean session teardown
on City_U1. START leaves the server and returns to the menu. Purchase UI did not
open in the observed test; early message text had malformed glyphs. Full combat,
vehicles, death/respawn, chat, round transitions and stable long-session behavior
remain unaccepted. Skirmish integration is not a claim of a fully tested mode.

For failures, retain the candidate-matched runtime log locally. Share only a
reviewed excerpt identifying the failing stage; remove credentials, identity
material and other players' records. A successful join is not a full campaign,
multiplayer, performance, or physical Vita acceptance result.
