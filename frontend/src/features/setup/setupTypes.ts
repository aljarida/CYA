export type DraftInventoryItem = {
  name: string;
  description: string;
  weightKg: number;
  quantity: number;
};

export type DraftAttributes = {
  ageYears: number;
  heightCm: number;
  bodyWeightKg: number;
  maxCarryWeightKg: number;
};

export type DraftStartingState = {
  startingLocation: string;
  startingInventory: DraftInventoryItem[];
  startingConditions: string[];
  attributes: DraftAttributes;
};
