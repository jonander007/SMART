{
    "General": {
        "Date": "08-11-2024",
        "Analyst": "CGT",
        "Description": "Very simple AHP example to choose a leader from https://en.wikipedia.org/wiki/Analytic_hierarchy_process_%E2%80%93_leader_example"
    },
    "Alternatives": {
        "Alternatives": [
            "Tom",
            "Dick",
            "Harry",
            "Pairwise Comparison"
        ]
    },
    "Criteria": {
        "Criteria": {
            "Choose a leader": {
                "children": [
                    "Age",
                    "Charisma",
                    "Education",
                    "Experience"
                ]
            }
        }
    },
    "Criteria Comparison": {
        "Criteria Comparison": {
            "Choose a leader": {
                "('Age', 'Charisma')": 0.2,
                "('Age', 'Education')": 0.3333333333333333,
                "('Age', 'Experience')": 0.14285714285714285,
                "('Charisma', 'Education')": 3,
                "('Charisma', 'Experience')": 0.3333333333333333,
                "('Education', 'Experience')": 0.25
            }
        }
    },
    "Alternative Rating": {
        "Age": {
            "('Tom', 'Dick')": 0.3333333333333333,
            "('Tom', 'Harry')": 5,
            "('Dick', 'Harry')": 9
        },
        "Charisma": {
            "('Tom', 'Dick')": 5,
            "('Tom', 'Harry')": 9,
            "('Dick', 'Harry')": 4
        },
        "Education": {
            "('Tom', 'Dick')": 3,
            "('Tom', 'Harry')": 0.2,
            "('Dick', 'Harry')": 0.14285714285714285
        },
        "Experience": {
            "('Tom', 'Dick')": 0.25,
            "('Tom', 'Harry')": 4,
            "('Dick', 'Harry')": 9
        }
    }
}