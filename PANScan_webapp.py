import csv
import os
import zipfile
import io
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
DATABASE_FILE = './Files/Database/classification_database.csv'
ALLOWED_EXTENSIONS = {'csv'}

# Create necessary folders
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max file size


def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def load_classification_database():
    """Load the classification database from CSV file."""
    classifications = []
    
    if not os.path.exists(DATABASE_FILE):
        return classifications
    
    with open(DATABASE_FILE, newline='', encoding="utf-8") as db_file:
        reader = csv.DictReader(db_file)
        for row in reader:
            classifications.append({
                'pattern': row['file_pattern'],
                'comments': row['comments'],
                'status': row['status']
            })
    
    return classifications


def classify_file(file_name, classifications):
    """Match filename against database patterns and return classification."""
    for item in classifications:
        if item['pattern'] in file_name:
            return item['comments'], item['status']
    
    return "", "Not Found"


def process_scan_file(input_path, output_path):
    """Process the uploaded scan file and generate reviewed output."""
    # Load classification database
    classifications = load_classification_database()
    
    # Statistics
    stats = {
        'true_positive': 0,
        'false_positive': 0,
        'not_found': 0,
        'total': 0
    }
    
    # Process input file
    with open(input_path, newline='', encoding="utf-8") as infile, \
         open(output_path, "w", newline='', encoding="utf-8") as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["Comments", "Findings"]
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            file_name = row.get("filename", "")
            
            # Classify the file
            comments, findings = classify_file(file_name, classifications)
            
            row["Comments"] = comments
            row["Findings"] = findings
            
            # Count statistics
            if findings == "True Positive":
                stats['true_positive'] += 1
            elif findings == "False Positive":
                stats['false_positive'] += 1
            else:
                stats['not_found'] += 1
            
            stats['total'] += 1
            
            writer.writerow(row)
    
    return stats


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and processing."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload a CSV file.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save uploaded file
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(input_path)
        
        # Generate output filename with "Reviewed_" prefix
        output_filename = f"Reviewed_{filename}"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{timestamp}_{output_filename}")
        
        # Process the file
        stats = process_scan_file(input_path, output_path)
        
        # Clean up uploaded file (optional - remove if you want to keep uploads)
        # os.remove(input_path)
        
        return render_template('result.html', 
                             filename=output_filename,
                             download_path=f"{timestamp}_{output_filename}",
                             stats=stats)
    
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download/<filename>')
def download_file(filename):
    """Handle file download."""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            flash('File not found', 'error')
            return redirect(url_for('index'))
        
        # Get the original filename without timestamp
        original_filename = '_'.join(filename.split('_')[2:]) if filename.count('_') >= 2 else filename
        
        return send_file(file_path, 
                        as_attachment=True, 
                        download_name=original_filename,
                        mimetype='text/csv')
    
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/bulk_scan', methods=['POST'])
def bulk_scan():
    """Handle bulk folder scanning."""
    folder_path = request.form.get('folder_path', '').strip()
    
    if not folder_path:
        flash('Please provide a folder path', 'error')
        return redirect(url_for('index'))
    
    if not os.path.exists(folder_path):
        flash('Folder path does not exist', 'error')
        return redirect(url_for('index'))
    
    if not os.path.isdir(folder_path):
        flash('Path is not a directory', 'error')
        return redirect(url_for('index'))
    
    try:
        # Find all CSV files in the folder
        csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.csv')]
        
        if not csv_files:
            flash('No CSV files found in the specified folder', 'error')
            return redirect(url_for('index'))
        
        print(f"Found {len(csv_files)} CSV files in {folder_path}")
        print(f"Files: {csv_files}")
        
        # Generate a unique session ID for this bulk scan
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Return the processing page with file list
        return render_template('bulk_processing.html', 
                             folder_path=folder_path,
                             csv_files=csv_files,
                             session_id=session_id)
    
    except Exception as e:
        print(f"Error in bulk_scan: {str(e)}")
        flash(f'Error processing folder: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/process_single_file', methods=['POST'])
def process_single_file():
    """Process a single file and return statistics."""
    try:
        data = request.get_json()
        folder_path = data.get('folder_path', '')
        file_name = data.get('file_name', '')
        session_id = data.get('session_id', '')
        
        print(f"\n=== Processing Single File Request ===")
        print(f"File name: {file_name}")
        print(f"Folder path: {folder_path}")
        print(f"Session ID: {session_id}")
        print(f"Folder path type: {type(folder_path)}")
        
        if not folder_path or not file_name or not session_id:
            print("ERROR: Missing parameters")
            return jsonify({
                'error': 'Missing parameters',
                'true_positive': 0,
                'false_positive': 0,
                'not_found': 0,
                'total': 0
            }), 400
        
        file_path = os.path.join(folder_path, file_name)
        print(f"Constructed file path: {file_path}")
        print(f"File path exists: {os.path.exists(file_path)}")
        print(f"Is file: {os.path.isfile(file_path)}")
        
        if not os.path.exists(file_path):
            print(f"ERROR: File not found at: {file_path}")
            print(f"Folder exists: {os.path.exists(folder_path)}")
            if os.path.exists(folder_path):
                print(f"Files in folder: {os.listdir(folder_path)}")
            return jsonify({
                'error': f'File not found: {file_path}',
                'true_positive': 0,
                'false_positive': 0,
                'not_found': 0,
                'total': 0
            }), 404
        
        # Load classification database
        classifications = load_classification_database()
        print(f"Loaded {len(classifications)} classifications from database")
        
        # Create output filename with session ID
        output_filename = f"{session_id}_Reviewed_{file_name}"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Process the file and save reviewed version
        print(f"Processing CSV file: {file_path}")
        stats = process_csv_and_save(file_path, output_path, classifications)
        
        print(f"Processing complete for {file_name}")
        print(f"Saved reviewed file: {output_path}")
        print(f"Results: {stats}")
        
        # Ensure all required fields are present
        response = {
            'true_positive': stats.get('true_positive', 0),
            'false_positive': stats.get('false_positive', 0),
            'not_found': stats.get('not_found', 0),
            'total': stats.get('total', 0),
            'success': True
        }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'true_positive': 0,
            'false_positive': 0,
            'not_found': 0,
            'total': 0,
            'success': False
        }), 500


def process_csv_for_bulk(file_path, classifications):
    """Process a CSV file and return statistics without creating output file."""
    stats = {
        'true_positive': 0,
        'false_positive': 0,
        'not_found': 0,
        'total': 0
    }
    
    with open(file_path, newline='', encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        
        for row in reader:
            file_name = row.get("filename", "")
            
            # Classify the file
            comments, findings = classify_file(file_name, classifications)
            
            # Count statistics
            if findings == "True Positive":
                stats['true_positive'] += 1
            elif findings == "False Positive":
                stats['false_positive'] += 1
            else:
                stats['not_found'] += 1
            
            stats['total'] += 1
    
    return stats


def process_csv_and_save(input_path, output_path, classifications):
    """Process a CSV file, save reviewed version, and return statistics."""
    stats = {
        'true_positive': 0,
        'false_positive': 0,
        'not_found': 0,
        'total': 0
    }
    
    with open(input_path, newline='', encoding="utf-8") as infile, \
         open(output_path, "w", newline='', encoding="utf-8") as outfile:
        
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + ["Comments", "Findings"]
        
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in reader:
            file_name = row.get("filename", "")
            
            # Classify the file
            comments, findings = classify_file(file_name, classifications)
            
            row["Comments"] = comments
            row["Findings"] = findings
            
            # Count statistics
            if findings == "True Positive":
                stats['true_positive'] += 1
            elif findings == "False Positive":
                stats['false_positive'] += 1
            else:
                stats['not_found'] += 1
            
            stats['total'] += 1
            
            writer.writerow(row)
    
    return stats


@app.route('/download_bulk_results/<session_id>', methods=['GET'])
def download_bulk_results(session_id):
    """Download all reviewed files from a bulk scan as a zip file."""
    try:
        # Find all files for this session
        output_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) 
                       if f.startswith(f"{session_id}_Reviewed_") and f.endswith('.csv')]
        
        if not output_files:
            flash('No reviewed files found for this session', 'error')
            return redirect(url_for('index'))
        
        # Create zip file in memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_name in output_files:
                file_path = os.path.join(app.config['OUTPUT_FOLDER'], file_name)
                # Add file to zip with cleaner name (remove session ID prefix)
                clean_name = file_name.replace(f"{session_id}_", "")
                zf.write(file_path, clean_name)
        
        memory_file.seek(0)
        
        # Send the zip file
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'BulkScan_Results_{session_id}.zip'
        )
    
    except Exception as e:
        print(f"Error creating zip file: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error downloading files: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download_single_result/<session_id>/<file_name>', methods=['GET'])
def download_single_result(session_id, file_name):
    """Download a single reviewed file from a bulk scan."""
    try:
        # Construct the reviewed filename
        reviewed_filename = f"{session_id}_Reviewed_{file_name}"
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], reviewed_filename)
        
        print(f"Download request for: {reviewed_filename}")
        print(f"File path: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"ERROR: File not found: {file_path}")
            flash('Reviewed file not found', 'error')
            return redirect(url_for('index'))
        
        # Send the file
        return send_file(
            file_path,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"Reviewed_{file_name}"
        )
    
    except Exception as e:
        print(f"Error downloading single file: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/cleanup_outputs', methods=['GET'])
def cleanup_outputs():
    """Delete all reviewed files from the outputs folder."""
    try:
        output_folder = app.config['OUTPUT_FOLDER']
        
        # Get all CSV files in outputs folder
        files = [f for f in os.listdir(output_folder) if f.endswith('.csv')]
        
        if not files:
            flash('No files to clean up', 'info')
            return redirect(url_for('index'))
        
        # Delete each file
        deleted_count = 0
        for file_name in files:
            file_path = os.path.join(output_folder, file_name)
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {file_name}: {str(e)}")
        
        print(f"Cleanup complete: Deleted {deleted_count} file(s) from outputs")
        flash(f'Successfully deleted {deleted_count} reviewed file(s)', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error during cleanup: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/cleanup_uploads', methods=['GET'])
def cleanup_uploads():
    """Delete all uploaded files from the uploads folder."""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        
        # Get all CSV files in uploads folder
        files = [f for f in os.listdir(upload_folder) if f.endswith('.csv')]
        
        if not files:
            flash('No files to clean up', 'info')
            return redirect(url_for('index'))
        
        # Delete each file
        deleted_count = 0
        for file_name in files:
            file_path = os.path.join(upload_folder, file_name)
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {file_name}: {str(e)}")
        
        print(f"Cleanup complete: Deleted {deleted_count} file(s) from uploads")
        flash(f'Successfully deleted {deleted_count} uploaded file(s)', 'success')
        return redirect(url_for('index'))
    
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error during cleanup: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/split_csv', methods=['POST'])
def split_csv():
    """Handle CSV file upload and splitting if needed."""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload a CSV file.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save uploaded file temporarily
        temp_input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{timestamp}_{filename}")
        file.save(temp_input_path)
        
        # Count rows in the CSV
        row_count = count_csv_rows(temp_input_path)
        
        print(f"CSV file has {row_count} rows")
        
        # Check if splitting is needed
        if row_count <= 1000000:
            # No splitting needed - just inform the user
            os.remove(temp_input_path)  # Clean up temp file
            flash(f'File has {row_count:,} rows. No splitting needed (threshold: 1 million rows).', 'info')
            return redirect(url_for('index'))
        
        # Split the CSV file
        split_files = split_csv_file(temp_input_path, filename, timestamp)
        
        # Clean up temp file
        os.remove(temp_input_path)
        
        # Create result data
        result_data = {
            'original_filename': filename,
            'total_rows': row_count,
            'split_files': split_files,
            'num_files': len(split_files)
        }
        
        return render_template('split_result.html', **result_data)
    
    except Exception as e:
        print(f"Error splitting CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('index'))


def count_csv_rows(file_path):
    """Count the number of rows in a CSV file (excluding header)."""
    with open(file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        # Skip header
        next(reader, None)
        row_count = sum(1 for row in reader)
    return row_count


def split_csv_file(input_path, original_filename, timestamp, chunk_size=1000000):
    """Split a CSV file into chunks of specified size."""
    split_files = []
    
    with open(input_path, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        
        file_num = 1
        row_num = 0
        current_writer = None
        current_file = None
        current_filename = None
        
        for row in reader:
            # Start a new file every chunk_size rows
            if row_num % chunk_size == 0:
                # Close previous file if exists
                if current_file:
                    current_file.close()
                
                # Create new file
                base_name = original_filename.rsplit('.', 1)[0]
                current_filename = f"{timestamp}_Split_{file_num}_{base_name}.csv"
                output_path = os.path.join(app.config['OUTPUT_FOLDER'], current_filename)
                
                current_file = open(output_path, 'w', newline='', encoding='utf-8')
                current_writer = csv.DictWriter(current_file, fieldnames=fieldnames)
                current_writer.writeheader()
                
                split_files.append({
                    'filename': current_filename,
                    'display_name': f"Part {file_num}",
                    'part_number': file_num
                })
                
                file_num += 1
            
            current_writer.writerow(row)
            row_num += 1
        
        # Close the last file
        if current_file:
            current_file.close()
    
    return split_files


@app.route('/download_split/<filename>')
def download_split_file(filename):
    """Download a split CSV file."""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        
        if not os.path.exists(file_path):
            flash('File not found', 'error')
            return redirect(url_for('index'))
        
        # Clean filename for download (remove timestamp prefix)
        parts = filename.split('_')
        if len(parts) >= 4:
            clean_name = '_'.join(parts[3:])
        else:
            clean_name = filename
        
        return send_file(file_path, 
                        as_attachment=True, 
                        download_name=clean_name,
                        mimetype='text/csv')
    
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/download_all_splits/<session_id>', methods=['GET'])
def download_all_splits(session_id):
    """Download all split files as a zip."""
    try:
        # Find all split files for this session
        split_files = [f for f in os.listdir(app.config['OUTPUT_FOLDER']) 
                      if f.startswith(f"{session_id}_Split_") and f.endswith('.csv')]
        
        if not split_files:
            flash('No split files found for this session', 'error')
            return redirect(url_for('index'))
        
        # Create zip file in memory
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_name in split_files:
                file_path = os.path.join(app.config['OUTPUT_FOLDER'], file_name)
                # Clean up filename in zip
                parts = file_name.split('_')
                clean_name = '_'.join(parts[3:]) if len(parts) >= 4 else file_name
                zf.write(file_path, clean_name)
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'Split_CSV_Files_{session_id}.zip'
        )
    
    except Exception as e:
        print(f"Error creating zip file: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error downloading files: {str(e)}', 'error')
        return redirect(url_for('index'))


if __name__ == '__main__':
    # Check if database file exists
    if not os.path.exists(DATABASE_FILE):
        print(f"WARNING: Classification database file '{DATABASE_FILE}' not found!")
        print("Please ensure the database file is in the same directory as this script.")
    
    print("\n" + "="*60)
    print("PANScan Web Application")
    print("="*60)
    print("Starting server...")
    print("Open your browser and navigate to: http://127.0.0.1:5000")
    print("Press CTRL+C to stop the server")
    print("="*60 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
