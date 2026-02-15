"""Patch seeds_resolved.json with manually verified corrections.

Fixes wrong matches from rate-limited fallback searches
and adds newly resolved papers.
"""

import json

PATCHES = {
    # --- Fixes for wrong matches ---
    "C17": {
        "semantic_scholar_id": "9595650ad0936d6ea96f61df7e7d7f35ac9f45e5",
        "s2_citation_count": 435,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    "M04": {
        "semantic_scholar_id": "9b0be8b83b80a7361fba60e2c94ede7e8a9e4baa",
        "s2_citation_count": 1,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    "M06": {
        "semantic_scholar_id": "8f05bac54b47e4ab12b91edd8e5e94c2a65b5e0f",
        "s2_citation_count": 1,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    "M11": {
        "semantic_scholar_id": "4740a5403d308fea74f784bb20ded0f25d99b1e0",
        "s2_citation_count": 9,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    # --- Newly resolved (were failed) ---
    "C04": {
        "semantic_scholar_id": "f798f288bbabe54eafcfc92f1fb1f65f82e71a71",
        "doi": "10.1109/icmas.1998.699041",
        "s2_citation_count": 898,
        "resolution_method": "crossref_doi_verified",
        "resolution_status": "resolved",
    },
    "C08": {
        "semantic_scholar_id": "ab2ed8b3a8cf141087a9b14cbc1f7a8ccb6ae2d3",
        "s2_citation_count": 376,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    "C13": {
        "semantic_scholar_id": "d621786b597687f555fae83dc1a021fd21713d90",
        "s2_citation_count": 7492,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    "C18": {
        "semantic_scholar_id": "361710c24db45a952a3b2b4b6f42ee0076e5e3e7",
        "s2_citation_count": 1114,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    "M02": {
        "semantic_scholar_id": "628dcc7046ea462b5e77b9c3c5b36f42a8f25c01",
        "doi": None,
        "arxiv_id": "2512.08296",
        "s2_citation_count": 18,
        "resolution_method": "arxiv_lookup_verified",
        "resolution_status": "resolved",
    },
    "M05": {
        "semantic_scholar_id": "5199f3540e8c79fd0d07c23d8b03c83c9cbdd86a",
        "s2_citation_count": 0,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    "M09": {
        "semantic_scholar_id": "7fa2d1632262f30907aec15add0fcf1ae22fa044",
        "s2_citation_count": 193,
        "resolution_method": "title_search_verified",
        "resolution_status": "resolved",
    },
    # --- Confirmed unresolvable ---
    "C02": {
        "resolution_status": "unresolvable",
        "resolution_note": "FIPA ACL is a specification document, not an academic paper. Not indexed in Semantic Scholar.",
    },
}


def main():
    with open("pipeline/data/seeds_resolved.json") as f:
        data = json.load(f)

    patched = 0
    for collection in ["classical_seeds", "modern_bridge"]:
        for seed in data[collection]:
            sid = seed["id"]
            if sid in PATCHES:
                patch = PATCHES[sid]
                seed.update(patch)
                patched += 1
                status = patch.get("resolution_status", "?")
                print(f"  Patched {sid}: {status} ({patch.get('resolution_method', patch.get('resolution_note', '?'))})")

    # Recompute stats
    all_seeds = data["classical_seeds"] + data["modern_bridge"]
    resolved = sum(1 for s in all_seeds if s.get("resolution_status") == "resolved")
    failed = sum(1 for s in all_seeds if s.get("resolution_status") == "unresolved")
    unresolvable = sum(1 for s in all_seeds if s.get("resolution_status") == "unresolvable")

    methods = {}
    for s in all_seeds:
        if s.get("resolution_status") == "resolved":
            m = s.get("resolution_method", "unknown")
            methods[m] = methods.get(m, 0) + 1

    data["stats"] = {
        "total": len(all_seeds),
        "resolved": resolved,
        "failed": failed,
        "unresolvable": unresolvable,
        "by_method": methods,
    }

    with open("pipeline/data/seeds_resolved.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nPatched {patched} entries")
    print(f"Resolved: {resolved}/{len(all_seeds)}")
    print(f"Failed: {failed}")
    print(f"Unresolvable: {unresolvable}")
    print(f"Methods: {json.dumps(methods, indent=2)}")


if __name__ == "__main__":
    main()
