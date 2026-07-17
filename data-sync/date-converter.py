import os
import argparse
from datetime import datetime

def convert_dates(input_path):
    # Automatically generate the output filename
    file_name, file_extension = os.path.splitext(input_path)
    output_path = f"{file_name}_normalized{file_extension}"
    
    # Flag to track whether we are inside the <start> and <end> block
    is_parsing = False
    
    with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
        for line in infile:
            date_str = line.strip()
            
            # Check for the markers
            if date_str == "<start>":
                is_parsing = True
                outfile.write("<start>\n")
                continue
            elif date_str == "<end>":
                if is_parsing:
                    outfile.write("<end>\n")
                break
                
            # If we are between <start> and <end>, process the lines
            if is_parsing:
                # Maintain empty lines
                if not date_str:
                    outfile.write('\n')
                    continue
                
                parsed_successfully = False
                
                # Try both 4-digit (%Y) and 2-digit (%y) year formats
                for fmt in ("%d-%b-%Y", "%d-%b-%y"):
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        new_date_str = date_obj.strftime("%Y-%m-%d")
                        
                        outfile.write(new_date_str + '\n')
                        print(f"Converted: {date_str} -> {new_date_str}")
                        parsed_successfully = True
                        break  # Stop checking formats once one works
                        
                    except ValueError:
                        continue  # Try the next format in the list
                
                # If neither format worked, report it as skipped
                if not parsed_successfully:
                    print(f"Skipped (Invalid format): {date_str}")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Convert dates between <start> and <end> tags to YYYY-MM-DD.")
    parser.add_argument('--input', required=True, help="Path to the input text file")
    
    args = parser.parse_args()
    input_file = args.input
    
    # Ensure the file exists before running
    if os.path.exists(input_file):
        convert_dates(input_file)
        
        # Get the dynamically generated output filename for the success message
        output_name = f"{os.path.splitext(input_file)[0]}_normalized{os.path.splitext(input_file)[1]}"
        print(f"\nConversion complete! Check '{output_name}'.")
    else:
        print(f"Error: The file '{input_file}' was not found.")