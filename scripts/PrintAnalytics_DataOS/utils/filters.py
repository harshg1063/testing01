def filter_by_uuid(df, uuid,hpx_flag):
    """Filter the DataFrame by a specific UUID."""
    if hpx_flag:
        return df[df['Associated Pc Device Uuid'] == uuid]
    else:
        return df[df['App Package Deployed Uuid'] == uuid]
