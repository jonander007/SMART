{
    "General": {
        "Date": "02-11-2024",
        "Analyst": "CGT",
        "Description": "Example with 2 Alternatives, 3 criteria, with 2 subcriteria using pairwise comparisons."
    },
    "Alternatives": {
        "Alternatives": [
            "Alternative1",
            "Alternative2",
            "Pairwise Comparison"
        ]
    },
    "Criteria": {
        "Criteria": {
            "Goal": {
                "children": [
                    {
                        "Criteria1": {
                            "children": [
                                "Subcriteria11",
                                "Subcriteria12"
                            ]
                        }
                    },
                    {
                        "Criteria2": {
                            "children": [
                                "Subcriteria21",
                                "Subcriteria22"
                            ]
                        }
                    },
                    {
                        "Criteria3": {
                            "children": [
                                "Subcriteria31",
                                "Subcriteria32"
                            ]
                        }
                    }
                ]
            }
        }
    },
    "Criteria Comparison": {
        "Criteria Comparison": {
            "Goal": {
                "('Criteria1', 'Criteria2')": 5,
                "('Criteria1', 'Criteria3')": 2,
                "('Criteria2', 'Criteria3')": 0.25
            },
            "Criteria1": {
                "('Subcriteria11', 'Subcriteria12')": 5
            },
            "Criteria2": {
                "('Subcriteria21', 'Subcriteria22')": 0.14285714285714285
            },
            "Criteria3": {
                "('Subcriteria31', 'Subcriteria32')": 7
            }
        }
    },
    "Alternative Rating": {
        "Subcriteria11": {
            "('Alternative1', 'Alternative2')": 5
        },
        "Subcriteria12": {
            "('Alternative1', 'Alternative2')": 0.25
        },
        "Subcriteria21": {
            "('Alternative1', 'Alternative2')": 8
        },
        "Subcriteria22": {
            "('Alternative1', 'Alternative2')": 8
        },
        "Subcriteria31": {
            "('Alternative1', 'Alternative2')": 0.14285714285714285
        },
        "Subcriteria32": {
            "('Alternative1', 'Alternative2')": 0.3333333333333333
        }
    }
}