import { Heart, Palmtree, Waves } from "lucide-react";
import { TravelModeSelector } from "@/components/TravelModeSelector";
import type { AccommodationType, SearchMode } from "@/lib/types";

const COMBINED_EXAMPLES = [
  {
    icon: Palmtree,
    label: "Azzorre o Canarie ad agosto",
    text: "Voglio andare in un posto tipo Azzorre o Canarie, non lontano da dove mi trovo, nella seconda metà di agosto per 1 settimana, 2 persone, max 750 € a testa volo+hotel, hotel minimo 4 stelle.",
  },
  {
    icon: Heart,
    label: "Weekend romantico a settembre",
    text: "Weekend romantico a settembre entro 400 € a testa, hotel 4 stelle.",
  },
  {
    icon: Waves,
    label: "Mare 7 notti sotto 600 EUR",
    text: "Una settimana di mare ad agosto per 2, budget 600 € a persona.",
  },
];

const EXAMPLES: Record<SearchMode, typeof COMBINED_EXAMPLES> = {
  flight_hotel: COMBINED_EXAMPLES,
  hotel_only: [
    {
      icon: Palmtree,
      label: "Soggiorno al mare ad agosto",
      text: "Cerco un alloggio al mare nella seconda metà di agosto per 7 notti, 2 persone, massimo 600 € a testa.",
    },
    {
      icon: Heart,
      label: "Weekend romantico a Roma",
      text: "Cerco un alloggio a Roma per un weekend romantico a settembre, 2 persone, entro 400 € a testa.",
    },
    {
      icon: Waves,
      label: "Casa per una settimana",
      text: "Cerco una casa vicino alla spiaggia per una settimana ad agosto, 2 persone, budget 500 € a persona.",
    },
  ],
  flight_only: [
    {
      icon: Palmtree,
      label: "Volo per le Canarie",
      text: "Cerco un volo andata e ritorno per le Canarie nella seconda metà di agosto, 2 persone, massimo 300 € a testa.",
    },
    {
      icon: Heart,
      label: "Weekend a Parigi",
      text: "Cerco un volo per Parigi per un weekend a settembre, 2 persone, entro 200 € a testa.",
    },
    {
      icon: Waves,
      label: "Volo economico per il mare",
      text: "Cerco un volo economico per una destinazione di mare ad agosto, 2 persone, budget 250 € a persona.",
    },
  ],
};

const MODE_COPY: Record<SearchMode, { title: string; description: string }> = {
  hotel_only: { title: "Dove vuoi soggiornare?", description: "Scegli hotel, case vacanza o entrambi e descrivi il soggiorno." },
  flight_only: { title: "Dove vuoi volare?", description: "Indicaci partenza, date, passeggeri e budget." },
  flight_hotel: { title: "Dove vuoi andare?", description: "Descrivi date, budget e stile del viaggio." },
};

export function EmptyState({
  onPick,
  mode,
  accommodationType,
  onModeChange,
  onAccommodationTypeChange,
}: {
  onPick: (t: string) => void;
  mode: SearchMode;
  accommodationType: AccommodationType;
  onModeChange: (mode: SearchMode) => void;
  onAccommodationTypeChange: (type: AccommodationType) => void;
}) {
  const copy = MODE_COPY[mode];
  return (
    <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col items-center justify-center gap-6 py-6 text-center md:py-10">
      <span className="grid size-14 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <Palmtree aria-hidden="true" />
      </span>
      <div className="flex max-w-2xl flex-col gap-3">
        <h1 className="text-4xl font-semibold leading-tight tracking-normal md:text-5xl">
          {copy.title}
        </h1>
        <p className="text-base text-muted-foreground md:text-lg">
          {copy.description}
        </p>
      </div>
      <TravelModeSelector
        mode={mode}
        accommodationType={accommodationType}
        onModeChange={onModeChange}
        onAccommodationTypeChange={onAccommodationTypeChange}
      />
      <div className="grid w-full gap-3 md:grid-cols-3">
        {EXAMPLES[mode].map((example) => (
          <button
            key={example.label}
            type="button"
            onClick={() => onPick(example.text)}
            className="group flex min-h-24 flex-col gap-3 rounded-lg border bg-card p-4 text-left shadow-sm transition hover:border-primary/40 hover:shadow-md"
          >
            <span className="grid size-9 place-items-center rounded-lg bg-primary/10 text-primary transition group-hover:bg-primary group-hover:text-primary-foreground">
              <example.icon aria-hidden="true" />
            </span>
            <span className="text-sm font-medium leading-5">{example.label}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
