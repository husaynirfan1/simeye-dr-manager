# DR Deficiency Management System - Web Application

A Flask-based web application for managing deficiencies in the PostgreSQL database.

## Features

- **Dashboard** - Overview with statistics and recent deficiencies
- **Full CRUD Operations** - Create, Read, Update, Delete deficiencies
- **Advanced Filtering** - Filter by status, severity, site, resource, and search across all fields
- **Action Tracking** - Add multiple actions to each deficiency with timestamps
- **All Column Support** - Supports all 46 columns from the dr_deficiency table
- **Responsive UI** - Modern Bootstrap-based interface

## Quick Start (Windows)

1. **Install Python 3.8+** (if not already installed)
   - Download from: https://www.python.org/
   - During installation, check "Add Python to PATH"

2. **Install Dependencies**
   ```cmd
   pip install -r requirements.txt
   ```

3. **Start the Server**
   - Double-click `start_server.bat`
   - OR run: `python app.py`

4. **Open in Browser**
   - Go to: http://localhost:5000

## Manual Start (Any Platform)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

The application will be available at http://localhost:5000

## Database Configuration

The database connection is configured in `app.py`:

```python
DB_CONFIG = {
    "dbname": "maintenance_app",
    "user": "postgres",
    "password": "pwneaw139",
    "host": "172.24.2.46",
    "port": "5432"
}
```

Edit these values if your database configuration is different.

## Usage

### Creating a Deficiency
1. Click "New Deficiency" in the navigation
2. Fill in the required fields (marked with *)
3. Optionally fill in additional details
4. Click "Create Deficiency"

### Viewing & Editing
1. Browse all deficiencies from "All Deficiencies" or use the dashboard
2. Click "View" to see full details and action history
3. Click "Edit" to modify deficiency details
4. Add actions from the view page

### Adding Actions
Actions are stored in the `ActionTaken` field with format:
```
[MMM DD YYYY HH:MMam/pm] [Username] [Action Description]
```

Multiple actions are separated and preserved when adding new ones.

### Filtering
Use the filter section to narrow down results:
- Search across DR#, Site, Resource, Issue Description
- Filter by Status, Severity, Site, Resource
- Combine multiple filters

## Screenshots

### Dashboard
- Shows total deficiencies, open items, cleared items
- Status and severity breakdown
- Recent deficiencies list

### List View
- Paginated table of all deficiencies
- Color-coded status and severity badges
- Quick filters and search

### Detail View
- Complete deficiency information
- Action history with parsed timestamps
- Add new action form

## API Endpoints

- `GET /` - Dashboard
- `GET /deficiencies` - List deficiencies (with filters)
- `GET /deficiency/<id>` - View single deficiency
- `GET /deficiency/new` - New deficiency form
- `POST /deficiency/new` - Create deficiency
- `GET /deficiency/<id>/edit` - Edit deficiency form
- `POST /deficiency/<id>/edit` - Update deficiency
- `POST /deficiency/<id>/action` - Add action
- `POST /deficiency/<id>/delete` - Delete deficiency
- `GET /api/search?q=query&field=field` - Search API
- `GET /api/deficiency/<id>` - Deficiency JSON API

## Security Notes

- Change the `SECRET_KEY` in `app.py` for production
- Use environment variables for database credentials in production
- Enable proper authentication before deploying
- Use a production WSGI server (e.g., Gunicorn) instead of Flask's development server

## Troubleshooting

### Database Connection Error
- Verify PostgreSQL is running
- Check host and port in DB_CONFIG
- Ensure network can reach the database server
- Verify username and password

### Template Not Found Error
- Ensure you're running from the correct directory
- Check that `templates/` folder exists

### Port Already in Use
- Change the port in `app.py`: `app.run(debug=True, host='0.0.0.0', port=5001)`

## File Structure

```
terminal-dr/
├── app.py                  # Flask application
├── requirements.txt        # Python dependencies
├── start_server.bat       # Windows startup script
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Dashboard
│   ├── errors/
│   │   ├── 404.html
│   │   └── 500.html
│   └── deficiencies/
│       ├── list.html      # List view
│       ├── view.html      # Detail view
│       ├── new.html       # Create form
│       └── edit.html      # Edit form
└── dr-client.py           # Original CLI client
```

## License

Internal use only.
