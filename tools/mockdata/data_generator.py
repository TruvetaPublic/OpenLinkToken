import csv
import sys

from faker import Faker

fake = Faker()

if len(sys.argv) != 4:
    print("Usage: python data_generator.py <num_lines> <repeat_probability> <output_file>")
    print("Using default values: num_lines=100, repeat_probability=0.05, output_file='test_data.csv'")
    num_lines = 100
    repeat_probability = 0.05
    output_file = "test_data.csv"
else:
    num_lines = int(sys.argv[1])
    repeat_probability = float(sys.argv[2])
    output_file = sys.argv[3]

# Open a CSV file to write the data
with open(output_file, mode="w", newline="") as file:
    writer = csv.writer(file)
    # Write the header
    writer.writerow(["RecordId", "BirthDate", "FirstName", "LastName", "PostalCode", "Sex", "SocialSecurityNumber"])

    # Define a cache to store generated values
    cache = []

    # Append random repeats to the cache
    num_repeats = int(num_lines * repeat_probability)
    num_lines_less_repeats = num_lines - num_repeats

    # Generate unique records and store them in the cache
    for _ in range(num_lines_less_repeats):
        record_id = fake.uuid4()
        birth_date = fake.date_of_birth(minimum_age=0, maximum_age=90)
        first_name = fake.first_name()
        last_name = fake.last_name()
        zip_code = fake.zipcode()
        sex = fake.random_element(elements=("Male", "Female"))
        ssn = fake.ssn()
        cache.append((record_id, birth_date, first_name, last_name, zip_code, sex, ssn))

    for _ in range(num_repeats):
        repeated_record = fake.random_element(cache)
        # Generate a new UUID for repeated record
        repeated_record = (fake.uuid4(),) + repeated_record[1:]
        cache.append(repeated_record)

    # Write all records to the CSV file
    for record in cache:
        # write record count every 1000 records
        if cache.index(record) % 1000 == 0:
            print(f"Writing record {cache.index(record)}")
        writer.writerow(record)

print(f"CSV file '{output_file}' created successfully.")
