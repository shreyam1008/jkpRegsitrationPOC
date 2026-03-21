import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft, ArrowRight, Save, Loader2, Check,
  User, CreditCard, MapPin, Settings,
} from "lucide-react";
import { createDevotee } from "@/api/satsangisApi";
import type { DevoteeCreate } from "@/api/satsangisApi";

// ─── Constants ───

const GENDER_OPTIONS = ["Male", "Female", "Other"] as const;
const SPECIAL_CATEGORIES = ["VIP", "Senior Citizen", "Differently Abled"] as const;
const NATIONALITY_OPTIONS = ["Indian", "Nepali", "American", "British", "Canadian", "Other"] as const;
const GOVT_ID_TYPES = ["Aadhar", "Passport", "Voter ID", "Driving License", "PAN Card"] as const;
const INTRODUCED_BY_OPTIONS = ["Preacher", "Online", "TV", "Person"] as const;

const STEPS = [
  { label: "Personal Info", icon: User },
  { label: "Documents", icon: CreditCard },
  { label: "Address", icon: MapPin },
  { label: "Other Details", icon: Settings },
] as const;

const EMPTY_FORM: DevoteeCreate = {
  first_name: "",
  last_name: "",
  phone_number: "",
  email: null,
  gender: null,
  date_of_birth: null,
  age: null,
  nationality: "Indian",
  special_category: null,
  nick_name: null,
  pan: null,
  govt_id_type: null,
  govt_id_number: null,
  id_expiry_date: null,
  id_issuing_country: null,
  country: "India",
  address: null,
  city: null,
  district: null,
  state: null,
  pincode: null,
  emergency_contact: null,
  introducer: null,
  introduced_by: null,
  ex_center_satsangi_id: null,
  print_on_card: false,
  has_room_in_ashram: false,
  banned: false,
  first_timer: false,
  date_of_first_visit: null,
  notes: null,
};

export function AddSatsangeePage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<DevoteeCreate>({ ...EMPTY_FORM });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const set = (field: keyof DevoteeCreate, value: unknown) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const isLastStep = step === STEPS.length - 1;

  const canProceed = () => {
    if (step === 0) return form.first_name.trim() && form.last_name.trim() && form.phone_number.trim();
    return true;
  };

  const handleNext = () => {
    if (isLastStep) return;
    setStep((s) => s + 1);
  };

  const handleBack = () => {
    if (step === 0) return;
    setStep((s) => s - 1);
  };

  const handleSubmit = async () => {
    setSaving(true);
    setError("");
    try {
      const created = await createDevotee(form);
      navigate({ to: "/satsangi/$id", params: { id: created.satsangi_id } });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      {/* Header */}
      <div className="mb-8 flex items-center gap-3">
        <button
          onClick={() => navigate({ to: "/" })}
          className="rounded-lg p-2 transition-colors hover:bg-hover"
          aria-label="Back"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-2xl font-bold tracking-tight">Add Satsangee</h1>
      </div>

      {/* ─── Stepper ─── */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            const isDone = i < step;
            const isActive = i === step;
            return (
              <div key={s.label} className="flex flex-1 items-center">
                <button
                  type="button"
                  onClick={() => i < step && setStep(i)}
                  className={[
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all",
                    isActive ? "bg-primary text-on-primary shadow-sm" : "",
                    isDone ? "text-success cursor-pointer hover:bg-hover" : "",
                    !isActive && !isDone ? "text-faint" : "",
                  ].join(" ")}
                >
                  <span className={[
                    "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                    isActive ? "bg-on-primary/20" : "",
                    isDone ? "bg-success/10" : "",
                    !isActive && !isDone ? "bg-hover" : "",
                  ].join(" ")}>
                    {isDone ? <Check size={14} /> : i + 1}
                  </span>
                  <span className="hidden sm:inline">{s.label}</span>
                </button>
                {i < STEPS.length - 1 && (
                  <div className={[
                    "mx-2 h-px flex-1",
                    i < step ? "bg-success" : "bg-border",
                  ].join(" ")} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-danger/30 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {/* ─── Step Content ─── */}
      <div className="rounded-2xl border border-border bg-surface p-6">
        {step === 0 && <StepPersonal form={form} set={set} />}
        {step === 1 && <StepDocuments form={form} set={set} />}
        {step === 2 && <StepAddress form={form} set={set} />}
        {step === 3 && <StepOther form={form} set={set} />}
      </div>

      {/* ─── Navigation Buttons ─── */}
      <div className="mt-6 flex items-center justify-between">
        <button
          type="button"
          onClick={step === 0 ? () => navigate({ to: "/" }) : handleBack}
          className="flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium text-muted transition-colors hover:bg-hover"
        >
          <ArrowLeft size={16} />
          {step === 0 ? "Cancel" : "Back"}
        </button>

        {isLastStep ? (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={saving || !canProceed()}
            className="flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-on-primary transition-opacity hover:opacity-80 disabled:opacity-50"
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
            {saving ? "Saving…" : "Save Satsangee"}
          </button>
        ) : (
          <button
            type="button"
            onClick={handleNext}
            disabled={!canProceed()}
            className="flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-on-primary transition-opacity hover:opacity-80 disabled:opacity-50"
          >
            Next
            <ArrowRight size={16} />
          </button>
        )}
      </div>
    </div>
  );
}

// ─── Step Components ───

type SetFn = (field: keyof DevoteeCreate, value: unknown) => void;

function StepPersonal({ form, set }: { form: DevoteeCreate; set: SetFn }) {
  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold">Personal Information</h2>
      <p className="mb-5 text-sm text-muted">Basic identity details of the satsangee</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="First Name *">
          <input required value={form.first_name} onChange={(e) => set("first_name", e.target.value)} className={INPUT} placeholder="e.g. Radha" />
        </Field>
        <Field label="Last Name *">
          <input required value={form.last_name} onChange={(e) => set("last_name", e.target.value)} className={INPUT} placeholder="e.g. Sharma" />
        </Field>
        <Field label="Phone Number *">
          <input required type="tel" value={form.phone_number} onChange={(e) => set("phone_number", e.target.value)} className={INPUT} placeholder="e.g. 9876543210" />
        </Field>
        <Field label="Email">
          <input type="email" value={form.email ?? ""} onChange={(e) => set("email", e.target.value || null)} className={INPUT} placeholder="e.g. radha@email.com" />
        </Field>
        <Field label="Gender">
          <select value={form.gender ?? ""} onChange={(e) => set("gender", e.target.value || null)} className={INPUT}>
            <option value="">Select</option>
            {GENDER_OPTIONS.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
        </Field>
        <Field label="Date of Birth">
          <input type="date" value={form.date_of_birth ?? ""} onChange={(e) => set("date_of_birth", e.target.value || null)} className={INPUT} />
        </Field>
        <Field label="Age">
          <input type="number" min={0} max={150} value={form.age ?? ""} onChange={(e) => set("age", e.target.value ? Number(e.target.value) : null)} className={INPUT} />
        </Field>
        <Field label="Nationality">
          <select value={form.nationality} onChange={(e) => set("nationality", e.target.value)} className={INPUT}>
            {NATIONALITY_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </Field>
        <Field label="Special Category">
          <select value={form.special_category ?? ""} onChange={(e) => set("special_category", e.target.value || null)} className={INPUT}>
            <option value="">None</option>
            {SPECIAL_CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </Field>
        <Field label="Nick Name">
          <input value={form.nick_name ?? ""} onChange={(e) => set("nick_name", e.target.value || null)} className={INPUT} />
        </Field>
        <Field label="PAN">
          <input value={form.pan ?? ""} onChange={(e) => set("pan", e.target.value || null)} className={INPUT} placeholder="e.g. ABCDE1234F" />
        </Field>
      </div>
    </div>
  );
}

function StepDocuments({ form, set }: { form: DevoteeCreate; set: SetFn }) {
  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold">Government Documents</h2>
      <p className="mb-5 text-sm text-muted">Identity verification documents</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="ID Type">
          <select value={form.govt_id_type ?? ""} onChange={(e) => set("govt_id_type", e.target.value || null)} className={INPUT}>
            <option value="">Select</option>
            {GOVT_ID_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="ID Number">
          <input value={form.govt_id_number ?? ""} onChange={(e) => set("govt_id_number", e.target.value || null)} className={INPUT} placeholder="e.g. 1234-5678-9012" />
        </Field>
        <Field label="ID Expiry Date">
          <input type="date" value={form.id_expiry_date ?? ""} onChange={(e) => set("id_expiry_date", e.target.value || null)} className={INPUT} />
        </Field>
        <Field label="ID Issuing Country">
          <input value={form.id_issuing_country ?? ""} onChange={(e) => set("id_issuing_country", e.target.value || null)} className={INPUT} placeholder="e.g. India" />
        </Field>
      </div>
      {!form.govt_id_type && (
        <p className="mt-4 rounded-lg bg-hover px-4 py-3 text-xs text-faint">
          You can skip this step if the satsangee does not have a government ID available right now.
        </p>
      )}
    </div>
  );
}

function StepAddress({ form, set }: { form: DevoteeCreate; set: SetFn }) {
  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold">Address</h2>
      <p className="mb-5 text-sm text-muted">Permanent address of the satsangee</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Country">
          <input value={form.country} onChange={(e) => set("country", e.target.value)} className={INPUT} />
        </Field>
        <Field label="State">
          <input value={form.state ?? ""} onChange={(e) => set("state", e.target.value || null)} className={INPUT} placeholder="e.g. Uttar Pradesh" />
        </Field>
        <Field label="District">
          <input value={form.district ?? ""} onChange={(e) => set("district", e.target.value || null)} className={INPUT} />
        </Field>
        <Field label="City / Town">
          <input value={form.city ?? ""} onChange={(e) => set("city", e.target.value || null)} className={INPUT} placeholder="e.g. Vrindavan" />
        </Field>
        <Field label="Pincode">
          <input value={form.pincode ?? ""} onChange={(e) => set("pincode", e.target.value || null)} className={INPUT} placeholder="e.g. 281121" />
        </Field>
        <div className="sm:col-span-2 lg:col-span-3">
          <Field label="Full Address">
            <textarea value={form.address ?? ""} onChange={(e) => set("address", e.target.value || null)} className={INPUT + " min-h-[80px] resize-y"} rows={3} placeholder="e.g. 211, Sample Apartments, Sector-X" />
          </Field>
        </div>
      </div>
    </div>
  );
}

function StepOther({ form, set }: { form: DevoteeCreate; set: SetFn }) {
  return (
    <div>
      <h2 className="mb-1 text-lg font-semibold">Other Details</h2>
      <p className="mb-5 text-sm text-muted">Contact, introduction, and registration details</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Field label="Emergency Contact">
          <input type="tel" value={form.emergency_contact ?? ""} onChange={(e) => set("emergency_contact", e.target.value || null)} className={INPUT} />
        </Field>
        <Field label="Introducer">
          <input value={form.introducer ?? ""} onChange={(e) => set("introducer", e.target.value || null)} className={INPUT} placeholder="Name of introducer" />
        </Field>
        <Field label="Introduced By">
          <select value={form.introduced_by ?? ""} onChange={(e) => set("introduced_by", e.target.value || null)} className={INPUT}>
            <option value="">Select</option>
            {INTRODUCED_BY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </Field>
        <Field label="Ex-Center Satsangi ID">
          <input value={form.ex_center_satsangi_id ?? ""} onChange={(e) => set("ex_center_satsangi_id", e.target.value || null)} className={INPUT} />
        </Field>
        <Field label="Date of First Visit">
          <input type="date" value={form.date_of_first_visit ?? ""} onChange={(e) => set("date_of_first_visit", e.target.value || null)} className={INPUT} />
        </Field>
      </div>
      <div className="mt-5 space-y-1">
        <Field label="Notes">
          <textarea value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value || null)} className={INPUT + " min-h-[80px] resize-y"} rows={3} placeholder="Any additional notes…" />
        </Field>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <ToggleCard label="Print on Card" checked={form.print_on_card ?? false} onChange={(v) => set("print_on_card", v)} />
        <ToggleCard label="Room in Ashram" checked={form.has_room_in_ashram ?? false} onChange={(v) => set("has_room_in_ashram", v)} />
        <ToggleCard label="First Timer" checked={form.first_timer ?? false} onChange={(v) => set("first_timer", v)} />
        <ToggleCard label="Banned" checked={form.banned ?? false} onChange={(v) => set("banned", v)} danger />
      </div>
    </div>
  );
}

// ─── Shared sub-components ───

const INPUT = "block w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-sm transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary placeholder:text-faint";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-muted">{label}</span>
      {children}
    </label>
  );
}

function ToggleCard({ label, checked, onChange, danger }: { label: string; checked: boolean; onChange: (v: boolean) => void; danger?: boolean }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={[
        "flex flex-col items-center gap-1.5 rounded-xl border p-3 text-center text-xs font-medium transition-all duration-150",
        checked
          ? danger
            ? "border-danger bg-danger/5 text-danger"
            : "border-primary bg-primary/5 text-primary"
          : "border-border text-faint hover:bg-hover hover:text-muted",
      ].join(" ")}
    >
      <div className={[
        "flex h-5 w-5 items-center justify-center rounded-md text-[10px]",
        checked
          ? danger ? "bg-danger text-on-danger" : "bg-primary text-on-primary"
          : "bg-hover",
      ].join(" ")}>
        {checked && <Check size={12} />}
      </div>
      {label}
    </button>
  );
}
