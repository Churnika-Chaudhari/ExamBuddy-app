"""Subject isolation checks for notes generation helpers."""

from app.utils.syllabus_modules import extract_subject_modules_from_catalog
from app.utils.syllabus_parser import collect_syllabus_catalog
from app.utils.module_filter import filter_module_tree


def test_catalog_does_not_mix_subjects():
    docs = [
        {
            "syllabus_structure": {
                "subjects": [{"name": "STQA", "units": []}],
                "catalog": [
                    {"subject": "STQA", "unit": "Module 1", "topic": "Regression Testing"},
                    {"subject": "SA", "unit": "Module 1", "topic": "Architectural Styles"},
                ],
                "subject_names": ["STQA", "SA"],
            }
        }
    ]
    stqa = collect_syllabus_catalog(docs, preferred_subject="STQA")
    sa = collect_syllabus_catalog(docs, preferred_subject="SA")
    assert stqa["topic_names"] == ["Regression Testing"]
    assert sa["topic_names"] == ["Architectural Styles"]
    assert all(r["subject"] == "STQA" for r in stqa["catalog"])
    assert all(r["subject"] == "SA" for r in sa["catalog"])


def test_modules_do_not_fall_back_to_other_subjects():
    catalog = [
        {"subject": "STQA", "unit": "Module 1 — Testing", "topic": "Regression Testing"},
        {"subject": "SA", "unit": "Module 1 — Styles", "topic": "Architectural Styles"},
    ]
    modules = extract_subject_modules_from_catalog(catalog, preferred_subject="STQA")
    topics = [t["topic"] for m in modules for t in m["topics"]]
    assert "Regression Testing" in topics
    assert "Architectural Styles" not in topics


def test_multi_module_filter_keeps_selected_only():
    modules = [
        {
            "module_id": "m1",
            "module_name": "Module 1",
            "topics": [{"topic": "A", "module_id": "m1", "occurrence_count": 1}],
        },
        {
            "module_id": "m2",
            "module_name": "Module 2",
            "topics": [{"topic": "B", "module_id": "m2", "occurrence_count": 2}],
        },
        {
            "module_id": "m4",
            "module_name": "Module 4",
            "topics": [{"topic": "C", "module_id": "m4", "occurrence_count": 3}],
        },
    ]
    filtered = filter_module_tree(
        modules=modules,
        topics=[t for m in modules for t in m["topics"]],
        selected_ids=["m1", "m2"],
    )
    names = [t["topic"] for t in filtered["topics"]]
    assert names == ["A", "B"]
    assert "C" not in names


if __name__ == "__main__":
    test_catalog_does_not_mix_subjects()
    test_modules_do_not_fall_back_to_other_subjects()
    test_multi_module_filter_keeps_selected_only()
    print("ok")
