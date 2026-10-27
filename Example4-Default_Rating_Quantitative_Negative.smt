{
    "General": {
        "Date": "02-11-2024",
        "Analyst": "CGT",
        "Description": "Example with 2 Alternatives, 3 criteria, with 2 subcriteria using qualitative (negative) and quantitative rating scales"
    },
    "Alternatives": {
        "Alternatives": [
            "Alternative1",
            "Alternative2",
            "Use Rating Scale"
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
        "Rating Scales Creation": {
            "Subcriteria11": [
                "High",
                "Medium",
                "Low",
                true
            ],
            "Subcriteria12": [
                "High",
                "Medium",
                "Low",
                false
            ],
            "Subcriteria21": [
                "High",
                "Medium",
                "Low",
                false
            ],
            "Subcriteria22": [
                "High",
                "Medium",
                "Low",
                false
            ],
            "Subcriteria31": [
                "High",
                "Medium",
                "Low",
                true
            ],
            "Subcriteria32": [
                "High",
                "Medium",
                "Low",
                false
            ]
        },
        "Rating Scales Comparison": {
            "Subcriteria12": {
                "('High', 'Medium')": 4,
                "('High', 'Low')": 8,
                "('Medium', 'Low')": 2
            },
            "Subcriteria21": {
                "('High', 'Medium')": 0.25,
                "('High', 'Low')": 0.125,
                "('Medium', 'Low')": 0.5
            },
            "Subcriteria22": {
                "('High', 'Medium')": 5,
                "('High', 'Low')": 9,
                "('Medium', 'Low')": 2
            },
            "Subcriteria32": {
                "('High', 'Medium')": 0.5,
                "('High', 'Low')": 0.3333333333333333,
                "('Medium', 'Low')": 0.5
            }
        },
        "Rating Table": {
            "Alternative1": {
                "Subcriteria11": "-5",
                "Subcriteria12": "Low",
                "Subcriteria21": "High",
                "Subcriteria22": "Medium",
                "Subcriteria31": "10",
                "Subcriteria32": "High"
            },
            "Alternative2": {
                "Subcriteria11": "10",
                "Subcriteria12": "Low",
                "Subcriteria21": "Medium",
                "Subcriteria22": "High",
                "Subcriteria31": "-7",
                "Subcriteria32": "High"
            }
        }
    }
}