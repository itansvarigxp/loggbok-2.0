# Nya kortläsare läser 4 bytes istället för 3, så vi tar endast de sista 3 bytesen

def process_card_number(card_number):
    # Nya kortläsare läser 4 bytes istället för 3, så vi tar endast de sista 3 bytesen
    card_number = hex(int(card_number, 10))
    # cursed som fan lol
    card_number = str(int(card_number[-6:], 16))
    return card_number

def normalize_card(raw: str) -> str:
    """Reader decimal -> lowest 3 bytes -> canonical decimal string."""
    return str(int(raw, 10) & 0xFFFFFF)



if __name__ == "__main__":
    card_number_old = "10214916"
    card_number_new = "0563863044"

    print(normalize_card(card_number_old))
    print(normalize_card(card_number_new))
    