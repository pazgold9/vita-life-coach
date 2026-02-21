"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { updateProfile, type UserProfile } from "@/lib/api";

interface ProfileFormProps {
  initialData: UserProfile;
  missingFields: string[];
  onSave: () => void;
  onCancel?: () => void;
}

const ACTIVITY_LEVELS = [
  { value: "sedentary", label: "Sedentary" },
  { value: "light", label: "Light" },
  { value: "moderate", label: "Moderate" },
  { value: "active", label: "Active" },
  { value: "very_active", label: "Very Active" },
];

const fieldLabels: Record<string, string> = {
  name: "Name",
  age: "Age",
  sex: "Sex",
  weight_kg: "Weight (kg)",
  height_cm: "Height (cm)",
  activity_level: "Activity Level",
  dietary_restrictions: "Dietary Restrictions",
  medical_conditions: "Medical Conditions",
  goals: "Goals",
};

export function ProfileForm({ initialData, missingFields, onSave, onCancel }: ProfileFormProps) {
  const [form, setForm] = useState<UserProfile>({
    name: initialData.name || "",
    age: initialData.age || undefined,
    sex: initialData.sex || "",
    weight_kg: initialData.weight_kg || undefined,
    height_cm: initialData.height_cm || undefined,
    activity_level: initialData.activity_level || "",
    dietary_restrictions: initialData.dietary_restrictions || "",
    medical_conditions: initialData.medical_conditions || "",
    goals: initialData.goals || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function isMissing(field: string) {
    return missingFields.includes(field);
  }

  function handleChange(field: keyof UserProfile, value: string | number) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    // Validate all fields are filled
    const missing: string[] = [];
    if (!form.name?.trim()) missing.push("name");
    if (!form.age && form.age !== 0) missing.push("age");
    if (!form.sex) missing.push("sex");
    if (!form.weight_kg && form.weight_kg !== 0) missing.push("weight_kg");
    if (!form.height_cm && form.height_cm !== 0) missing.push("height_cm");
    if (!form.activity_level) missing.push("activity_level");
    if (!form.dietary_restrictions?.trim()) missing.push("dietary_restrictions");
    if (!form.medical_conditions?.trim()) missing.push("medical_conditions");
    if (!form.goals?.trim()) missing.push("goals");

    if (missing.length > 0) {
      setError(`Please fill in all fields: ${missing.map(f => fieldLabels[f]).join(", ")}`);
      return;
    }

    setSaving(true);
    setError(null);

    const payload = {
      name: form.name!.trim(),
      age: Number(form.age),
      sex: form.sex,
      weight_kg: Number(form.weight_kg),
      height_cm: Number(form.height_cm),
      activity_level: form.activity_level,
      dietary_restrictions: form.dietary_restrictions!.trim(),
      medical_conditions: form.medical_conditions!.trim(),
      goals: form.goals!.trim(),
    };

    try {
      await updateProfile(payload);
      onSave();
    } catch {
      setError("Failed to save profile. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  const inputClass = (field: string) =>
    `h-8 text-xs ${isMissing(field) ? "ring-2 ring-red-500/50 border-red-500/50" : ""}`;

  const selectClass = (field: string) =>
    `h-8 text-xs w-full rounded-md border px-2 bg-background ${isMissing(field) ? "ring-2 ring-red-500/50 border-red-500/50" : "border-input"}`;

  return (
    <form onSubmit={handleSubmit} className="space-y-2.5">
      <div>
        <label className="text-xs text-muted-foreground">{fieldLabels.name} *</label>
        <Input
          className={inputClass("name")}
          placeholder="Your name"
          value={form.name || ""}
          onChange={(e) => handleChange("name", e.target.value)}
        />
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="text-xs text-muted-foreground">{fieldLabels.age} *</label>
          <Input
            className={inputClass("age")}
            type="number"
            placeholder="25"
            min={10}
            max={120}
            value={form.age || ""}
            onChange={(e) => handleChange("age", e.target.value ? Number(e.target.value) : "")}
          />
        </div>
        <div className="flex-1">
          <label className="text-xs text-muted-foreground">{fieldLabels.sex} *</label>
          <select
            className={selectClass("sex")}
            value={form.sex || ""}
            onChange={(e) => handleChange("sex", e.target.value)}
          >
            <option value="">Select</option>
            <option value="male">Male</option>
            <option value="female">Female</option>
          </select>
        </div>
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="text-xs text-muted-foreground">{fieldLabels.weight_kg} *</label>
          <Input
            className={inputClass("weight_kg")}
            type="number"
            placeholder="70"
            min={20}
            max={300}
            value={form.weight_kg || ""}
            onChange={(e) => handleChange("weight_kg", e.target.value ? Number(e.target.value) : "")}
          />
        </div>
        <div className="flex-1">
          <label className="text-xs text-muted-foreground">{fieldLabels.height_cm} *</label>
          <Input
            className={inputClass("height_cm")}
            type="number"
            placeholder="175"
            min={50}
            max={250}
            value={form.height_cm || ""}
            onChange={(e) => handleChange("height_cm", e.target.value ? Number(e.target.value) : "")}
          />
        </div>
      </div>

      <div>
        <label className="text-xs text-muted-foreground">{fieldLabels.activity_level} *</label>
        <select
          className={selectClass("activity_level")}
          value={form.activity_level || ""}
          onChange={(e) => handleChange("activity_level", e.target.value)}
        >
          <option value="">Select level</option>
          {ACTIVITY_LEVELS.map((l) => (
            <option key={l.value} value={l.value}>{l.label}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-xs text-muted-foreground">{fieldLabels.dietary_restrictions} *</label>
        <Input
          className={inputClass("dietary_restrictions")}
          placeholder="e.g., vegan, gluten-free, none"
          value={form.dietary_restrictions || ""}
          onChange={(e) => handleChange("dietary_restrictions", e.target.value)}
        />
      </div>

      <div>
        <label className="text-xs text-muted-foreground">{fieldLabels.medical_conditions} *</label>
        <Input
          className={inputClass("medical_conditions")}
          placeholder="e.g., diabetes, none"
          value={form.medical_conditions || ""}
          onChange={(e) => handleChange("medical_conditions", e.target.value)}
        />
      </div>

      <div>
        <label className="text-xs text-muted-foreground">{fieldLabels.goals} *</label>
        <Input
          className={inputClass("goals")}
          placeholder="e.g., lose weight, build muscle"
          value={form.goals || ""}
          onChange={(e) => handleChange("goals", e.target.value)}
        />
      </div>

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}

      <div className="flex gap-2 pt-1">
        <Button type="submit" size="sm" className="flex-1" disabled={saving}>
          {saving ? "Saving..." : "Save Profile"}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </form>
  );
}
