Add persistent profile storage and CLI profile commands

- Add filesystem-backed PasswordProfile repository under path from PASS_GEN_GIT_PERSISTENCE_PATH.
- Store profiles in sharded JSON layout: profiles/<2-char-shard>/<sha256(username:resource)>.json.
- Replace single CLI entry with command group: create, set, get.
- Wire get command to load profile constraints from persistent storage before password generation.
- Add tests for repository operations, storage layout, and CLI create/set/get flow.
