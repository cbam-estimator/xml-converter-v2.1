from src.validator import process_and_validate


def test_validator():
    input, validate = process_and_validate("production_method", "P45 - Something")

    print(f"1 - Input: {input}, Validate: {validate}")

    input, validate = process_and_validate("production_method", "P45")

    print(f"2 - Input: {input}, Validate: {validate}")
