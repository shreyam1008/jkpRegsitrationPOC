import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router'
import { useForm, type UseFormRegisterReturn } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { createSatsangi } from '../api'
import { clsx } from 'clsx'
import {
  User, MapPin, Settings, ArrowLeft, Loader2, CheckCircle2, AlertCircle, Send,
  Phone, Calendar, CreditCard, Globe, Shield, Camera, Check, ChevronDown,
  FileText, ClipboardList,
} from 'lucide-react'

const GENDERS = ['Male', 'Female', 'Other']
const SPECIAL_CATEGORIES = ['None', 'Senior Citizen', 'Disabled', 'VIP']
const NATIONALITIES = ['Indian', 'Nepali', 'Other']
const GOVT_ID_TYPES = ['Aadhar Card', 'Passport', 'Voter ID', 'Driving License', 'Nagrita (Nepal)']
const COUNTRIES = ['India', 'Nepal', 'USA', 'UK', 'Canada', 'Australia', 'Other']
const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa',
  'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
  'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland',
  'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana', 'Tripura',
  'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi', 'Jammu & Kashmir',
  'Ladakh', 'Chandigarh', 'Puducherry',
]
const INTRODUCED_BY = ['Preacher', 'Online', 'TV', 'Person']

const schema = z.object({
  firstName: z.string().min(1, 'First name is required').max(100),
  lastName: z.string().min(1, 'Last name is required').max(100),
  phoneNumber: z.string().min(1, 'Phone number is required').max(20),
  age: z.coerce.number().int().min(1).max(150).optional().or(z.literal('')),
  dateOfBirth: z.string().optional(),
  pan: z.string().max(20).optional(),
  gender: z.string().optional(),
  specialCategory: z.string().optional(),
  nationality: z.string().min(1, 'Required'),
  govtIdType: z.string().optional(),
  govtIdNumber: z.string().max(50).optional(),
  idExpiryDate: z.string().optional(),
  idIssuingCountry: z.string().optional(),
  nickName: z.string().max(100).optional(),
  printOnCard: z.boolean(),
  introducer: z.string().max(200).optional(),
  country: z.string().min(1, 'Required'),
  address: z.string().optional(),
  city: z.string().max(100).optional(),
  district: z.string().max(100).optional(),
  state: z.string().optional(),
  pincode: z.string().max(10).optional(),
  emergencyContact: z.string().max(20).optional(),
  exCenterSatsangiId: z.string().max(20).optional(),
  introducedBy: z.string().optional(),
  hasRoomInAshram: z.boolean(),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
  banned: z.boolean(),
  firstTimer: z.boolean(),
  dateOfFirstVisit: z.string().optional(),
  notes: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

export default function CreatePage() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    mode: 'onChange',
    defaultValues: {
      nationality: 'Indian',
      country: 'India',
      printOnCard: false,
      hasRoomInAshram: false,
      banned: false,
      firstTimer: false,
    },
  })

  const { register, handleSubmit, formState: { errors } } = form

  useEffect(() => {
    if (!success) return
    const id = window.setTimeout(() => navigate('/search'), 2000)
    return () => clearTimeout(id)
  }, [success, navigate])

  async function onSubmit(data: FormValues) {
    setError('')
    setSuccess('')
    setSubmitting(true)

    const cleaned = {
      ...data,
      age: typeof data.age === 'number' ? data.age : undefined,
      email: data.email || undefined,
    }

    try {
      const created = await createSatsangi(cleaned)
      setSuccess(`Registered! Satsangi ID: ${created.satsangiId}`)
      form.reset()
      setPhotoPreview(null)
    } catch {
      setError('Failed to register. Please check your details and try again.')
    } finally {
      setSubmitting(false)
    }
  }

  function handlePhoto(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => setPhotoPreview(ev.target?.result as string)
    reader.readAsDataURL(file)
  }

  return (
    <div>
      {/* Back */}
      <button
        type="button"
        onClick={() => navigate('/search')}
        className="mb-4 flex items-center gap-1.5 text-[13px] font-medium text-gray-400 hover:text-gray-600 transition-colors"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to Search
      </button>

      <h1 className="text-xl font-bold text-gray-900 tracking-tight">Add New Devotee</h1>
      <p className="mt-0.5 text-[13px] text-gray-400 mb-6">Fill in all sections to register a new satsangi</p>

      {/* Alerts */}
      {error && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 font-medium">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* Two-column layout: 50/50 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* ── LEFT COLUMN ── */}
          <div className="space-y-6">

            {/* Personal */}
            <Section icon={User} title="Personal">
              <Row>
                <Field label="First Name" error={errors.firstName?.message} required>
                  <input {...register('firstName')} placeholder="Enter first name" className={inputCls(errors.firstName)} />
                </Field>
                <Field label="Last Name" error={errors.lastName?.message} required>
                  <input {...register('lastName')} placeholder="Enter last name" className={inputCls(errors.lastName)} />
                </Field>
              </Row>
              <Row>
                <Field label="Phone Number" error={errors.phoneNumber?.message} required icon={<Phone className="h-4 w-4" />}>
                  <input {...register('phoneNumber')} type="tel" placeholder="+91 98765 43210" className={inputCls(errors.phoneNumber, true)} />
                </Field>
                <Field label="Age" error={errors.age?.message}>
                  <input {...register('age')} type="number" placeholder="e.g. 35" className={inputCls(errors.age)} />
                </Field>
              </Row>
              <Row>
                <Field label="Date of Birth" icon={<Calendar className="h-4 w-4" />}>
                  <input {...register('dateOfBirth')} type="date" className={inputCls(undefined, true)} />
                </Field>
                <Field label="PAN" icon={<CreditCard className="h-4 w-4" />}>
                  <input {...register('pan')} placeholder="ABCDE1234F" className={inputCls(undefined, true)} />
                </Field>
              </Row>
              <Row>
                <Field label="Gender">
                  <SelectField register={register('gender')} options={GENDERS} />
                </Field>
                <Field label="Special Category">
                  <SelectField register={register('specialCategory')} options={SPECIAL_CATEGORIES} />
                </Field>
              </Row>
              <Row>
                <Field label="Nationality" error={errors.nationality?.message} required>
                  <SelectField register={register('nationality')} options={NATIONALITIES} />
                </Field>
                <Field label="Nick Name">
                  <input {...register('nickName')} placeholder="Optional nickname" className={inputCls()} />
                </Field>
              </Row>
              <Row>
                <Field label="Introducer">
                  <input {...register('introducer')} placeholder="Name of introducer" className={inputCls()} />
                </Field>
                <Field label="Print on Card">
                  <label className="mt-1 flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-2.5 cursor-pointer hover:border-gray-300 has-[:checked]:border-brand-500 has-[:checked]:bg-brand-50/50 transition-all">
                    <input type="checkbox" {...register('printOnCard')} className="peer sr-only" />
                    <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 border-gray-300 peer-checked:border-brand-600 peer-checked:bg-brand-600 transition-all">
                      <Check className="h-3 w-3 text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                    </div>
                    <span className="text-sm text-gray-600 peer-checked:text-brand-700">Yes, print on card</span>
                  </label>
                </Field>
              </Row>
            </Section>

            {/* Address */}
            <Section icon={MapPin} title="Address">
              <Row>
                <Field label="Country" error={errors.country?.message} required>
                  <SelectField register={register('country')} options={COUNTRIES} />
                </Field>
                <Field label="State">
                  <SelectField register={register('state')} options={INDIAN_STATES} />
                </Field>
              </Row>
              <Field label="Street Address" icon={<MapPin className="h-4 w-4" />}>
                <textarea {...register('address')} rows={3} placeholder="e.g. 271, Sample Apartments, Sec-X" className={inputCls(undefined, true)} />
              </Field>
              <Row>
                <Field label="City / Town">
                  <input {...register('city')} placeholder="Enter city" className={inputCls()} />
                </Field>
                <Field label="District">
                  <input {...register('district')} placeholder="Enter district" className={inputCls()} />
                </Field>
              </Row>
              <Field label="Pincode">
                <input {...register('pincode')} placeholder="e.g. 201010" className={inputCls()} />
              </Field>
            </Section>

            {/* Gov ID */}
            <Section icon={Shield} title="Government ID">
              <Row>
                <Field label="ID Type">
                  <SelectField register={register('govtIdType')} options={GOVT_ID_TYPES} />
                </Field>
                <Field label="ID Number">
                  <input {...register('govtIdNumber')} placeholder="Enter ID number" className={inputCls()} />
                </Field>
              </Row>
              <Row>
                <Field label="Expiry Date">
                  <input {...register('idExpiryDate')} type="date" className={inputCls()} />
                </Field>
                <Field label="Issuing Country">
                  <SelectField register={register('idIssuingCountry')} options={COUNTRIES} />
                </Field>
              </Row>
            </Section>

            {/* Other */}
            <Section icon={Settings} title="Other">
              <Row>
                <Field label="Emergency Contact" icon={<Phone className="h-4 w-4" />}>
                  <input {...register('emergencyContact')} type="tel" placeholder="+91 98765 43210" className={inputCls(undefined, true)} />
                </Field>
                <Field label="Ex-center Satsangi ID">
                  <input {...register('exCenterSatsangiId')} placeholder="Enter ID if available" className={inputCls()} />
                </Field>
              </Row>
              <Field label="Email" error={errors.email?.message} icon={<Globe className="h-4 w-4" />}>
                <input {...register('email')} type="email" placeholder="user@example.com" className={inputCls(errors.email, true)} />
              </Field>
              <Field label="Notes">
                <textarea {...register('notes')} rows={3} placeholder="Any additional notes…" className={inputCls()} />
              </Field>
            </Section>
          </div>

          {/* ── RIGHT COLUMN ── */}
          <div className="space-y-6">

            {/* Visit */}
            <Section icon={ClipboardList} title="Visit">
              <Field label="Date of First Visit" icon={<Calendar className="h-4 w-4" />}>
                <input {...register('dateOfFirstVisit')} type="date" className={inputCls(undefined, true)} />
              </Field>
              <Field label="Introduced By">
                <div className="flex flex-wrap gap-2">
                  {INTRODUCED_BY.map((opt) => (
                    <label
                      key={opt}
                      className="group flex cursor-pointer items-center gap-2 rounded-xl border border-gray-200 bg-white px-4 py-2.5 hover:border-gray-300 has-[:checked]:border-brand-500 has-[:checked]:bg-brand-50/50 transition-all"
                    >
                      <input type="radio" value={opt} {...register('introducedBy')} className="peer sr-only" />
                      <div className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2 border-gray-300 peer-checked:border-brand-600 transition-all">
                        <div className="h-2 w-2 rounded-full bg-brand-600 scale-0 peer-checked:scale-100 transition-transform" />
                      </div>
                      <span className="text-sm font-medium text-gray-600 peer-checked:text-brand-700 transition-colors">{opt}</span>
                    </label>
                  ))}
                </div>
              </Field>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <CheckboxCard label="First Timer" register={register('firstTimer')} />
                <CheckboxCard label="Has Room in Ashram" register={register('hasRoomInAshram')} />
              </div>
              <CheckboxCard label="Banned" register={register('banned')} danger />
            </Section>

            {/* Documents */}
            <Section icon={FileText} title="Documents">
              {/* Photo upload */}
              <Field label="Photo">
                <label className="photo-upload relative flex h-32 w-full cursor-pointer items-center justify-center rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50 hover:border-brand-300 hover:bg-brand-50/30 transition-all overflow-hidden">
                  {photoPreview ? (
                    <img src={photoPreview} alt="Preview" className="h-full w-full object-contain" />
                  ) : (
                    <div className="text-center">
                      <Camera className="h-8 w-8 text-gray-300 mx-auto" />
                      <span className="text-[12px] text-gray-400 mt-1.5 block">Click to upload photo</span>
                    </div>
                  )}
                  <div className="photo-overlay absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 transition-opacity">
                    <Camera className="h-6 w-6 text-white" />
                  </div>
                  <input type="file" accept="image/*" className="sr-only" onChange={handlePhoto} />
                </label>
              </Field>
            </Section>
          </div>
        </div>

        {/* Submit button */}
        <div className="flex justify-end pt-6 mt-6 border-t border-gray-100">
          <button
            type="submit"
            disabled={submitting}
            className={clsx(
              'flex items-center gap-2.5 rounded-xl px-6 py-2.5 text-sm font-semibold text-white',
              'bg-brand-600 hover:bg-brand-700 active:bg-brand-800',
              'shadow-sm shadow-brand-600/20 hover:shadow-md',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'transition-all duration-200',
            )}
          >
            {submitting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</>
            ) : (
              <><Send className="h-4 w-4" /> Register Devotee</>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

function Section({ icon: Icon, title, children }: { icon: React.ComponentType<{ className?: string }>; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-100 bg-white p-5 space-y-4 shadow-sm">
      <div className="flex items-center gap-2 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
        <Icon className="h-3.5 w-3.5" />
        {title}
      </div>
      {children}
    </div>
  )
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{children}</div>
}

function Field({ label, error, required, icon, children }: {
  label: string; error?: string; required?: boolean; icon?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="group">
      <label className="mb-1.5 flex items-baseline gap-1 text-[13px] font-semibold text-gray-600 tracking-wide">
        {label}
        {required && <span className="text-red-400 text-xs">*</span>}
      </label>
      <div className="relative">
        {icon && (
          <div className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-brand-500 transition-colors z-10">
            {icon}
          </div>
        )}
        {children}
      </div>
      {error && <p className="mt-1 text-[12px] text-red-500 font-medium">{error}</p>}
    </div>
  )
}

function inputCls(error?: { message?: string }, hasIcon?: boolean) {
  return clsx(
    'block w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm text-gray-900',
    'placeholder:text-gray-400 transition-all duration-200',
    'hover:border-gray-300',
    'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
    hasIcon && 'pl-10',
    error ? 'border-red-300 focus:ring-red-500/20 focus:border-red-500' : 'border-gray-200',
  )
}

function SelectField({ register: reg, options }: { register: UseFormRegisterReturn; options: string[] }) {
  return (
    <div className="relative">
      <select
        {...reg}
        className={clsx(
          'block w-full appearance-none rounded-xl border border-gray-200 bg-white',
          'px-3.5 py-2.5 pr-10 text-sm text-gray-900',
          'transition-all duration-200 hover:border-gray-300',
          'focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500',
        )}
      >
        <option value="">Select…</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
    </div>
  )
}

function CheckboxCard({ label, register: reg, danger }: { label: string; register: UseFormRegisterReturn; danger?: boolean }) {
  return (
    <label className={clsx(
      'group flex cursor-pointer items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3',
      'transition-all duration-200 hover:border-gray-300 hover:shadow-sm',
      danger
        ? 'has-[:checked]:border-red-500 has-[:checked]:bg-red-50/50'
        : 'has-[:checked]:border-brand-500 has-[:checked]:bg-brand-50/50',
    )}>
      <input type="checkbox" {...reg} className="peer sr-only" />
      <div className={clsx(
        'flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 transition-all duration-200',
        danger
          ? 'border-gray-300 peer-checked:border-red-500 peer-checked:bg-red-500'
          : 'border-gray-300 peer-checked:border-brand-600 peer-checked:bg-brand-600',
      )}>
        <Check className="h-3 w-3 text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
      </div>
      <span className={clsx(
        'text-sm font-medium transition-colors',
        danger ? 'text-gray-600 peer-checked:text-red-700' : 'text-gray-600 peer-checked:text-brand-700',
      )}>{label}</span>
    </label>
  )
}
