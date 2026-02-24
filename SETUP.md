# PANScan Web Application - Setup Guide

## Overview

PANScan is a Flask-based web application for automated file pattern classification and analysis. It scans CSV files against a classification database to identify patterns and categorize data as True Positive, False Positive, or Not Found.

## Prerequisites

### 1. Python
- **Version Required:** Python 3.8 or higher
- **Check if installed:**
  ```powershell
  python --version
  ```
- **Download:** If not installed, download from [python.org](https://www.python.org/downloads/)

### 2. pip (Python Package Installer)
- Usually comes with Python installation
- **Check if installed:**
  ```powershell
  pip --version
  ```

- **Install pip if not present:**
  
  If pip is not installed, download and install it:
  
  ```powershell
  # Install pip if not already installed
  python.exe -m pip install --upgrade pip
  ```
  
  Or use the Python ensurepip module:
  ```powershell
  python -m ensurepip --upgrade
  ```
  
  After installation, verify:
  ```powershell
  pip --version
  ```

## Installation

### Step 1: Navigate to the Application Directory
Open PowerShell or Command Prompt and navigate to the PANScan folder:
```powershell
cd C:\Users\118260\Documents\PANScan
```

### Step 2: Install Dependencies
Install Flask and required packages:
```powershell
pip install -r requirements.txt
```

**Alternative methods:**
```powershell
python -m pip install -r requirements.txt
```

Or install packages individually:
```powershell
pip install Flask==3.0.0 Werkzeug==3.0.1
```

### Step 3: Verify File Structure
Ensure the following structure exists:

```
PANScan/
├── PANScan_webapp.py               # Main Flask application
├── requirements.txt                 # Python dependencies
├── SETUP.md                         # This setup guide
├── Files/
│   └── Database/
│       └── classification_database.csv   # Classification rules
├── templates/                       # HTML templates
│   ├── index.html                  # Main upload page
│   ├── result.html                 # Single file results
│   ├── bulk_processing.html        # Bulk scan processing
│   └── bulk_result.html            # Bulk scan results
├── uploads/                         # Temporary file storage (auto-created)
├── outputs/                         # Processed output files (auto-created)
└── Reviewed/                        # Optional: reviewed files storage
```

### Step 4: Verify Database File
The classification database must exist at `Files/Database/classification_database.csv`. This file contains:
- `file_pattern`: Patterns to match against
- `comments`: Classification descriptions
- `status`: True Positive or False Positive

## Running the Application

### Starting the Server
From the PANScan directory, run:
```powershell
python PANScan_webapp.py
```

You should see:
```
====================================================================
PANScan Web Application
====================================================================
Starting server...
Open your browser and navigate to: http://127.0.0.1:5000
Press CTRL+C to stop the server
====================================================================
```

### Accessing the Application
Open your browser and navigate to:
- **http://127.0.0.1:5000** or
- **http://localhost:5000**

## Features and Usage

### 1. Single File Upload Mode
**Best for:** Processing individual CSV files

1. Click the upload area or drag-and-drop your CSV file
2. Click "Process File" to begin analysis
3. View results showing:
   - True Positive count
   - False Positive count
   - Not Found count
   - Detailed breakdown by pattern
4. Download the reviewed file (prefixed with `Reviewed_`)
5. Click "Process Another File" for additional scans

### 2. Bulk Folder Scan Mode
**Best for:** Processing multiple CSV files at once

1. Enter the full folder path containing CSV files
2. Click "Scan Folder"
3. The system will:
   - Detect all CSV files in the folder
   - Process each file sequentially
   - Display real-time progress
4. View aggregate statistics for all files
5. Download individual results or a ZIP archive of all processed files

### 3. File Management
The application includes utilities for cleanup:
- Uploaded files are stored temporarily in `uploads/`
- Processed files are saved in `outputs/` with timestamp prefixes
- Large files supported up to 200MB

## Configuration

### Application Settings
Edit `PANScan_webapp.py` to customize:

```python
# Maximum file upload size (default: 200MB)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

# Server host and port (default: localhost:5000)
app.run(debug=True, host='127.0.0.1', port=5000)

# Secret key (CHANGE THIS for production)
app.secret_key = 'your-secret-key-change-this-in-production'
```

### Database Path
```python
DATABASE_FILE = './Files/Database/classification_database.csv'
```

## Stopping the Application

Press `CTRL + C` in the terminal where the application is running.

## Troubleshooting

### Issue: "Module not found" Error
**Cause:** Dependencies not installed  
**Solution:**
```powershell
pip install -r requirements.txt
```

### Issue: Port 5000 Already in Use
**Cause:** Another application is using port 5000  
**Solution 1:** Stop the other application  
**Solution 2:** Change the port in `PANScan_webapp.py`:
```python
app.run(debug=True, host='127.0.0.1', port=5001)
```

### Issue: "classification_database.csv not found"
**Cause:** Database file missing or incorrect path  
**Solution:** Verify the file exists at `Files/Database/classification_database.csv`

### Issue: Can't Access from Another Computer
**Cause:** Server only listening on localhost  
**Solution:** Change host to `0.0.0.0` (use only on trusted networks):
```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

### Issue: Upload Fails with Large Files
**Cause:** File exceeds size limit  
**Solution:** Increase `MAX_CONTENT_LENGTH` in configuration

### Issue: Bulk Scan Not Finding Files
**Cause:** Invalid folder path or no CSV files present  
**Solution:**
- Verify the folder path is correct
- Ensure CSV files exist in the specified folder
- Check file permissions

## Production Deployment

For production environments:

### Security
1. **Change the secret key:**
   ```python
   import secrets
   app.secret_key = secrets.token_hex(32)
   ```

2. **Disable debug mode:**
   ```python
   app.run(debug=False, host='127.0.0.1', port=5000)
   ```

3. **Use a production WSGI server:**
   ```powershell
   pip install gunicorn
   gunicorn -w 4 -b 127.0.0.1:5000 PANScan_webapp:app
   ```

### Recommendations
- Implement user authentication/authorization
- Configure HTTPS/TLS for secure communications
- Set up automated cleanup of old files in `uploads/` and `outputs/`
- Configure proper logging and error handling
- Use environment variables for sensitive configuration
- Implement rate limiting for uploads
- Set up database backups

## Technical Details

### Dependencies
- **Flask 3.0.0**: Web framework
- **Werkzeug 3.0.1**: WSGI utility library

### File Processing Flow
1. File uploaded to `uploads/` folder
2. Classification database loaded
3. CSV rows analyzed against classification patterns
4. Results categorized (True Positive, False Positive, Not Found)
5. Reviewed file generated in `outputs/` with timestamp prefix
6. Statistics calculated and displayed

### Supported File Formats
- **Input:** CSV files only (UTF-8 encoding)
- **Output:** CSV files with classification columns added
- **Max Size:** 200MB per file

## Maintenance

### Regular Tasks
- Monitor disk space in `uploads/` and `outputs/` folders
- Review and update `classification_database.csv` as needed
- Check application logs for errors
- Update dependencies periodically:
  ```powershell
  pip install --upgrade Flask Werkzeug
  ```

### Cleanup Utilities
The application includes built-in cleanup endpoints:
- `/cleanup_outputs`: Remove old processed files
- `/cleanup_uploads`: Remove temporary uploaded files

## Support

For issues, questions, or contributions:
- Review this documentation thoroughly
- Check the [Flask documentation](https://flask.palletsprojects.com/)
- Verify all prerequisites are correctly installed
- Ensure the classification database is properly formatted

## Version Information
- **Last Updated:** February 2026
- **Python Version:** 3.8+
- **Flask Version:** 3.0.0
