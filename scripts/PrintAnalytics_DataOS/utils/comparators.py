def compare_dataframes(spec_df, filtered_df, compare_columns):
    """Compare spec_df against filtered_df and count occurrences of full matching rows."""
    
    # Create a dictionary { (col1, col2, col3, col4): occurrence count }
    count_map = filtered_df.groupby(compare_columns).size().to_dict()

    # Prepare results list
    results = []
    for _, row in spec_df.iterrows():
        spec_tuple = tuple(row[compare_columns])  # Convert row to tuple for lookup
        count = count_map.get(spec_tuple, 0)  # Count occurrences of the full row
        result = 'Pass' if count > 0 else 'Fail'
        results.append((result, count))

    # Assign results back to spec_df
    spec_df['result'] = [result for result, count in results]
    spec_df['count'] = [count for result, count in results]

    return spec_df  # Now contains unique rows with correct counts
