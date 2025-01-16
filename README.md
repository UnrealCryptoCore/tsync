# T-Sync

moodle test comparison tool

## Development

- (install modules: `sudo pacman -S python-bcrypt python-dotenv`)
- create db: `python src/tsync/db_setup.py setup`
- start server: `flask --app src.tsync run`
- build the package: `python -m build --wheel`
