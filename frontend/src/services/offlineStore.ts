import { openDB, type DBSchema, type IDBPDatabase } from "idb";

import type { SavedTrip } from "../types/api";

interface PahadPathDatabase extends DBSchema {
  trips: {
    key: string;
    value: SavedTrip;
    indexes: { "by-saved-at": string };
  };
}

const DATABASE_NAME = "pahadpath-trips";
const DATABASE_VERSION = 1;
let databasePromise: Promise<IDBPDatabase<PahadPathDatabase>> | undefined;

function database(): Promise<IDBPDatabase<PahadPathDatabase>> {
  databasePromise ??= openDB<PahadPathDatabase>(DATABASE_NAME, DATABASE_VERSION, {
    upgrade(db) {
      const store = db.createObjectStore("trips", { keyPath: "id" });
      store.createIndex("by-saved-at", "saved_at");
    },
  });
  return databasePromise;
}

export async function saveTrip(trip: SavedTrip): Promise<void> {
  const db = await database();
  await db.put("trips", trip);
}

export async function listSavedTrips(): Promise<SavedTrip[]> {
  const db = await database();
  return (await db.getAllFromIndex("trips", "by-saved-at")).reverse();
}

export async function getSavedTrip(id: string): Promise<SavedTrip | undefined> {
  return (await database()).get("trips", id);
}

export async function deleteSavedTrip(id: string): Promise<void> {
  await (await database()).delete("trips", id);
}
