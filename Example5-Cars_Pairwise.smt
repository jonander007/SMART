{
    "General": {
        "Date": "02-11-2024",
        "Analyst": "CGT",
        "Description": "Selection of Car from https://en.wikipedia.org/wiki/Analytic_hierarchy_process_%E2%80%93_car_example (Note: Slight differences due to approximations in the Maintenance and Fuel Costs Ratings)"
    },
    "Alternatives": {
        "Alternatives": [
            "Accord Sedan",
            "Accord Hybrid",
            "Pilot",
            "CR-V",
            "Element",
            "Odyssey",
            "Pairwise Comparison"
        ]
    },
    "Criteria": {
        "Criteria": {
            "Selection of Car": {
                "children": [
                    {
                        "Capacity": {
                            "children": [
                                "Cargo",
                                "Passenger"
                            ]
                        }
                    },
                    {
                        "Cost": {
                            "children": [
                                "Fuel Cost",
                                "Maintenance Cost",
                                "Purchase Price",
                                "Resale"
                            ]
                        }
                    },
                    "Safety",
                    "Style"
                ]
            }
        }
    },
    "Criteria Comparison": {
        "Criteria Comparison": {
            "Selection of Car": {
                "('Capacity', 'Cost')": 0.3333333333333333,
                "('Capacity', 'Safety')": 1,
                "('Capacity', 'Style')": 7,
                "('Cost', 'Safety')": 3,
                "('Cost', 'Style')": 7,
                "('Safety', 'Style')": 9
            },
            "Capacity": {
                "('Cargo', 'Passenger')": 0.2
            },
            "Cost": {
                "('Fuel Cost', 'Maintenance Cost')": 2,
                "('Fuel Cost', 'Purchase Price')": 0.5,
                "('Fuel Cost', 'Resale')": 2,
                "('Maintenance Cost', 'Purchase Price')": 0.2,
                "('Maintenance Cost', 'Resale')": 0.5,
                "('Purchase Price', 'Resale')": 3
            }
        }
    },
    "Alternative Rating": {
        "Cargo": {
            "('Accord Sedan', 'Accord Hybrid')": 1,
            "('Accord Sedan', 'Pilot')": 0.5,
            "('Accord Sedan', 'CR-V')": 0.5,
            "('Accord Sedan', 'Element')": 0.5,
            "('Accord Sedan', 'Odyssey')": 0.3333333333333333,
            "('Accord Hybrid', 'Pilot')": 0.5,
            "('Accord Hybrid', 'CR-V')": 0.5,
            "('Accord Hybrid', 'Element')": 0.5,
            "('Accord Hybrid', 'Odyssey')": 0.3333333333333333,
            "('Pilot', 'CR-V')": 1,
            "('Pilot', 'Element')": 1,
            "('Pilot', 'Odyssey')": 0.5,
            "('CR-V', 'Element')": 1,
            "('CR-V', 'Odyssey')": 0.5,
            "('Element', 'Odyssey')": 0.5
        },
        "Passenger": {
            "('Accord Sedan', 'Accord Hybrid')": 1,
            "('Accord Sedan', 'Pilot')": 0.5,
            "('Accord Sedan', 'CR-V')": 1,
            "('Accord Sedan', 'Element')": 3,
            "('Accord Sedan', 'Odyssey')": 0.5,
            "('Accord Hybrid', 'Pilot')": 0.5,
            "('Accord Hybrid', 'CR-V')": 1,
            "('Accord Hybrid', 'Element')": 3,
            "('Accord Hybrid', 'Odyssey')": 0.5,
            "('Pilot', 'CR-V')": 2,
            "('Pilot', 'Element')": 6,
            "('Pilot', 'Odyssey')": 1,
            "('CR-V', 'Element')": 3,
            "('CR-V', 'Odyssey')": 0.5,
            "('Element', 'Odyssey')": 0.16666666666666666
        },
        "Fuel Cost": {
            "('Accord Sedan', 'Accord Hybrid')": 0.5,
            "('Accord Sedan', 'Pilot')": 6,
            "('Accord Sedan', 'CR-V')": 3,
            "('Accord Sedan', 'Element')": 4,
            "('Accord Sedan', 'Odyssey')": 3,
            "('Accord Hybrid', 'Pilot')": 9,
            "('Accord Hybrid', 'CR-V')": 5,
            "('Accord Hybrid', 'Element')": 6,
            "('Accord Hybrid', 'Odyssey')": 6,
            "('Pilot', 'CR-V')": 0.25,
            "('Pilot', 'Element')": 0.5,
            "('Pilot', 'Odyssey')": 0.3333333333333333,
            "('CR-V', 'Element')": 2,
            "('CR-V', 'Odyssey')": 1,
            "('Element', 'Odyssey')": 1
        },
        "Maintenance Cost": {
            "('Accord Sedan', 'Accord Hybrid')": 1,
            "('Accord Sedan', 'Pilot')": 4,
            "('Accord Sedan', 'CR-V')": 4,
            "('Accord Sedan', 'Element')": 4,
            "('Accord Sedan', 'Odyssey')": 5,
            "('Accord Hybrid', 'Pilot')": 4,
            "('Accord Hybrid', 'CR-V')": 4,
            "('Accord Hybrid', 'Element')": 4,
            "('Accord Hybrid', 'Odyssey')": 5,
            "('Pilot', 'CR-V')": 1,
            "('Pilot', 'Element')": 1,
            "('Pilot', 'Odyssey')": 1,
            "('CR-V', 'Element')": 1,
            "('CR-V', 'Odyssey')": 3,
            "('Element', 'Odyssey')": 2
        },
        "Purchase Price": {
            "('Accord Sedan', 'Accord Hybrid')": 9,
            "('Accord Sedan', 'Pilot')": 9,
            "('Accord Sedan', 'CR-V')": 1,
            "('Accord Sedan', 'Element')": 0.5,
            "('Accord Sedan', 'Odyssey')": 5,
            "('Accord Hybrid', 'Pilot')": 1,
            "('Accord Hybrid', 'CR-V')": 0.1111111111111111,
            "('Accord Hybrid', 'Element')": 0.1111111111111111,
            "('Accord Hybrid', 'Odyssey')": 0.14285714285714285,
            "('Pilot', 'CR-V')": 0.1111111111111111,
            "('Pilot', 'Element')": 0.1111111111111111,
            "('Pilot', 'Odyssey')": 0.14285714285714285,
            "('CR-V', 'Element')": 0.5,
            "('CR-V', 'Odyssey')": 5,
            "('Element', 'Odyssey')": 6
        },
        "Resale": {
            "('Accord Sedan', 'Accord Hybrid')": 3,
            "('Accord Sedan', 'Pilot')": 4,
            "('Accord Sedan', 'CR-V')": 0.5,
            "('Accord Sedan', 'Element')": 2,
            "('Accord Sedan', 'Odyssey')": 2,
            "('Accord Hybrid', 'Pilot')": 2,
            "('Accord Hybrid', 'CR-V')": 0.2,
            "('Accord Hybrid', 'Element')": 1,
            "('Accord Hybrid', 'Odyssey')": 1,
            "('Pilot', 'CR-V')": 0.16666666666666666,
            "('Pilot', 'Element')": 0.5,
            "('Pilot', 'Odyssey')": 0.5,
            "('CR-V', 'Element')": 4,
            "('CR-V', 'Odyssey')": 4,
            "('Element', 'Odyssey')": 1
        },
        "Safety": {
            "('Accord Sedan', 'Accord Hybrid')": 1,
            "('Accord Sedan', 'Pilot')": 5,
            "('Accord Sedan', 'CR-V')": 7,
            "('Accord Sedan', 'Element')": 9,
            "('Accord Sedan', 'Odyssey')": 0.3333333333333333,
            "('Accord Hybrid', 'Pilot')": 5,
            "('Accord Hybrid', 'CR-V')": 7,
            "('Accord Hybrid', 'Element')": 9,
            "('Accord Hybrid', 'Odyssey')": 0.3333333333333333,
            "('Pilot', 'CR-V')": 2,
            "('Pilot', 'Element')": 9,
            "('Pilot', 'Odyssey')": 0.125,
            "('CR-V', 'Element')": 2,
            "('CR-V', 'Odyssey')": 0.125,
            "('Element', 'Odyssey')": 0.1111111111111111
        },
        "Style": {
            "('Accord Sedan', 'Accord Hybrid')": 1,
            "('Accord Sedan', 'Pilot')": 7,
            "('Accord Sedan', 'CR-V')": 5,
            "('Accord Sedan', 'Element')": 9,
            "('Accord Sedan', 'Odyssey')": 6,
            "('Accord Hybrid', 'Pilot')": 7,
            "('Accord Hybrid', 'CR-V')": 5,
            "('Accord Hybrid', 'Element')": 9,
            "('Accord Hybrid', 'Odyssey')": 6,
            "('Pilot', 'CR-V')": 0.16666666666666666,
            "('Pilot', 'Element')": 3,
            "('Pilot', 'Odyssey')": 0.3333333333333333,
            "('CR-V', 'Element')": 7,
            "('CR-V', 'Odyssey')": 5,
            "('Element', 'Odyssey')": 0.2
        }
    }
}