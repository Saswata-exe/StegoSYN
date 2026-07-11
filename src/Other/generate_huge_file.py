import os

def generate_file(file_path, target_size, paragraph):
    """
    Create a text file of exactly `target_size` characters by repeating `paragraph`.
    The final copy is truncated to reach the exact size.
    """
    para_len = len(paragraph)
    if target_size <= 0:
        # Create an empty file if size is 0 or negative
        open(file_path, 'w').close()
        return

    with open(file_path, 'w', encoding='utf-8') as f:
        remaining = target_size
        while remaining > 0:
            if remaining >= para_len:
                f.write(paragraph)
                remaining -= para_len
            else:
                # Write only the first `remaining` characters of the paragraph
                f.write(paragraph[:remaining])
                remaining = 0

    print(f"File '{file_path}' created with {target_size} characters.")

if __name__ == "__main__":
    # The exact paragraph given in the problem
    PARAGRAPH = (
        "Intelligence reports indicate that a terrorist training camp is operating in a remote mountainous region "
        "across the border. After weeks of surveillance using satellites, reconnaissance aircraft, and intelligence "
        "sources, the government authorizes a limited counterterrorism operation aimed solely at dismantling the camp "
        "while minimizing civilian harm.\n\n"
        "Before the mission begins, nearby civilian areas are carefully identified and excluded from the target zone. "
        "Diplomatic and military channels are kept open to reduce the risk of unintended escalation.\n\n"
        "A specialized military unit infiltrates the area under cover of darkness. After confirming the absence of "
        "civilians, they secure the perimeter and neutralize armed resistance. The camp's communications equipment, "
        "weapons storage, and logistical infrastructure are disabled.\n\n"
        "Once the objective is achieved, the force withdraws without occupying territory. The government later announces "
        "that the operation was directed exclusively against a terrorist organization and not against civilians or the "
        "neighboring country's military.\n\n"
        "Independent assessments are conducted to verify the outcome and evaluate any humanitarian impact."
    )

    try:
        size = int(input("Enter the desired file size (number of characters): "))
        if size < 0:
            print("Size cannot be negative. Using 0.")
            size = 0
        # You can change the output file name as needed
        output_file = "huge_text.txt"
        generate_file(output_file, size, PARAGRAPH)

        # Show the actual file size for verification
        actual_size = os.path.getsize(output_file)
        print(f"Actual file size: {actual_size} characters.")
    except ValueError:
        print("Invalid input. Please enter an integer.")
    except Exception as e:
        print(f"An error occurred: {e}")
