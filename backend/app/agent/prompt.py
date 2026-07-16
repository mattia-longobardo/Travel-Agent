def build_system_prompt(params: dict) -> str:
    lines = [
        "Sei un agente di viaggio. Usa i tool disponibili (voli, hotel, lastminute) per "
        "cercare e confrontare prezzi reali. Restituisci SEMPRE più opzioni (almeno 2-3) "
        "ordinate per rapporto qualità/prezzo, ognuna con prezzo, date, luogo e link se disponibile.",
    ]
    if params.get("destination"):
        if params.get("destination_flexible"):
            lines.append(f"Destinazione preferita: {params['destination']}, ma è FLESSIBILE: "
                         "proponi anche mete alternative simili se più convenienti.")
        else:
            lines.append(f"Destinazione FISSA: {params['destination']}.")
    if params.get("origin"):
        lines.append(f"Partenza da: {params['origin']}.")
    if params.get("dates_flexible"):
        lines.append("Le date sono FLESSIBILI: prova combinazioni diverse nel periodo indicato "
                     "per trovare i prezzi migliori.")
    elif params.get("check_in"):
        lines.append(f"Date FISSE: {params.get('check_in')} → {params.get('check_out')}.")
    if params.get("budget"):
        kind = params.get("budget_type", "max")
        lines.append(f"Budget ({kind}): {params['budget']} {params.get('currency','EUR')}. "
                     "Non superarlo se è un massimo; segnala se nessuna opzione rientra.")
    if params.get("travelers"):
        lines.append(f"Viaggiatori: {params['travelers']}.")
    if params.get("min_stars"):
        lines.append(f"Hotel con almeno {params['min_stars']} stelle.")
    if params.get("good_reviews"):
        lines.append("Preferisci hotel con buone recensioni (rating alto).")
    return "\n".join(lines)
