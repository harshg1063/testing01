'''-------------------HOW TO RUN----------------
 1. Create a a folder under Print Analytics (Ex: data_folder)
 2. Keep Spec and downloaded Data OS data in folder . Make sure both are in CSV format.
 3. Trigger the code as below   
        For HPX : python main.py "data_folder\actual.csv" "data_folder\spec.csv" <uuid> true
        For HP Smart : python main.py "data_folder\actual.csv" "data_folder\spec.csv" <uuid> false
'''

import argparse
import os

from utils.comparators import compare_dataframes
from utils.file_operations import load_csv, save_csv
from utils.filters import filter_by_uuid
from utils.transformations import rename_columns, split_and_duplicate_rows

def main(actual_csv, spec_csv, uuid,hpx_flag):
    # Load CSV files
    actual_df = load_csv(actual_csv)
    spec_df = load_csv(spec_csv)

    # Filter actual CSV by UUID
    filtered_df = filter_by_uuid(actual_df, uuid,hpx_flag)

    # Rename columns for consistency
    filtered_df = rename_columns(filtered_df,hpx_flag)

    # Ensure consistent formatting
    spec_df.columns = spec_df.columns.str.strip()
    spec_df['screenMode'].fillna("None", inplace=True)
    filtered_df['screenMode'].fillna("None", inplace=True)

    # Split 'screenMode' into multiple rows
    spec_df = split_and_duplicate_rows(spec_df, 'screenMode')
    filtered_df = split_and_duplicate_rows(filtered_df, 'screenMode')

    # Define columns for comparison
    compare_columns = ['screenName', 'screenMode', 'action', 'controlName']

    # Compare spec and actual data
    final_result = compare_dataframes(spec_df, filtered_df, compare_columns)

    # Save results to separate files
    passed_results_path = os.path.join('data', 'passed_results.csv')
    failed_results_path = os.path.join('data', 'failed_results.csv')
    save_csv(final_result[final_result['result'] == 'Pass'], passed_results_path)
    save_csv(final_result[final_result['result'] == 'Fail'], failed_results_path)

    print(f"Results saved to:\n- {passed_results_path}\n- {failed_results_path}")


if __name__ == "__main__":
    parser =argparse.ArgumentParser(description='Compare two CSV files based on specific criteria.')
    parser.add_argument('actual_csv', type=str, help='Path to the actual CSV file')
    parser.add_argument('spec_csv', type=str, help='Path to the spec CSV file')
    parser.add_argument('uuid', type=str, help='UUID to filter the actual CSV file')
    parser.add_argument('hpx_flag',type=bool, help='pass as true while testing hpx')
    args = parser.parse_args()

    main(args.actual_csv, args.spec_csv, args.uuid,args.hpx_flag)
    
