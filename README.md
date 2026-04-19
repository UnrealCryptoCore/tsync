# T-Sync

moodle test comparison tool

## Development

### Setup

To initialize the project run the following commands:
`bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
`

To setup the database run 
`bash
python src/tsync/db_setup.py setup
`

### Start Server
`bash
flask --app src.tsync run
`


## Production

Build the package using
`bash
python -m build --wheel
`
