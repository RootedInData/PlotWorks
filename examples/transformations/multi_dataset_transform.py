"""Example generated transformation for named traits and metadata inputs.

Register sample_id as a string in both inputs. Metadata contains a group column.
The wrapper supplies the datasets, validates code, and manages output publication.
"""


def transform_data(datasets):
    traits = datasets["traits"].copy()
    # Keep absent metadata keys unmatched for this left join.
    metadata = datasets["metadata"].dropna(subset=["sample_id"]).copy()
    joined = traits.merge(metadata, on="sample_id", how="left", validate="many_to_one")
    unmatched = joined[joined["group"].isna()].copy()
    return {"plot_ready": joined, "unmatched": unmatched}
