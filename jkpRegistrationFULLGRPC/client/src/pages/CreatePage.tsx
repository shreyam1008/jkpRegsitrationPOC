import { useState, useEffect, useRef, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { createSatsangi } from '../api'
import type { SatsangiCreate } from '../api'
import CollapsibleSection from '../components/ui/CollapsibleSection'
import FormInput from '../components/ui/FormInput'
import FormSelect from '../components/ui/FormSelect'
import FormCheckbox from '../components/ui/FormCheckbox'
import FormRadioGroup from '../components/ui/FormRadioGroup'
import {
  User, MapPin, Settings, ArrowLeft, Loader2, CheckCircle2, AlertCircle, Send,
  Phone, Calendar, CreditCard, Globe, Shield,
} from 'lucide-react'
import { clsx } from 'clsx'

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

export default function CreatePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const formRef = useRef<HTMLFormElement>(null)

  useEffect(() => {
    if (!success) return
    const id = window.setTimeout(() => navigate('/search'), 1500)
    return () => clearTimeout(id)
  }, [success, navigate])

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    const fd = new FormData(e.currentTarget)
    const str = (key: string) => (fd.get(key) as string)?.trim() || null
    const first_name = str('first_name')
    const last_name = str('last_name')
    const phone_number = str('phone_number')

    if (!first_name || !last_name || !phone_number) {
      setError('First Name, Last Name and Phone Number are required.')
      setLoading(false)
      return
    }

    const ageRaw = str('age')
    const payload: Partial<SatsangiCreate> = {
      firstName: first_name!,
      lastName: last_name!,
      phoneNumber: phone_number!,
      age: ageRaw ? parseInt(ageRaw, 10) : undefined,
      dateOfBirth: str('date_of_birth') ?? undefined,
      pan: str('pan') ?? undefined,
      gender: str('gender') ?? undefined,
      specialCategory: str('special_category') ?? undefined,
      nationality: str('nationality') ?? 'Indian',
      govtIdType: str('govt_id_type') ?? undefined,
      govtIdNumber: str('govt_id_number') ?? undefined,
      idExpiryDate: str('id_expiry_date') ?? undefined,
      idIssuingCountry: str('id_issuing_country') ?? undefined,
      nickName: str('nick_name') ?? undefined,
      printOnCard: fd.get('print_on_card') === 'on',
      introducer: str('introducer') ?? undefined,
      country: str('country') ?? 'India',
      address: str('address') ?? undefined,
      city: str('city') ?? undefined,
      district: str('district') ?? undefined,
      state: str('state') ?? undefined,
      pincode: str('pincode') ?? undefined,
      emergencyContact: str('emergency_contact') ?? undefined,
      exCenterSatsangiId: str('ex_center_satsangi_id') ?? undefined,
      introducedBy: str('introduced_by') ?? undefined,
      hasRoomInAshram: fd.get('has_room_in_ashram') === 'on',
      email: str('email') ?? undefined,
      banned: fd.get('banned') === 'on',
      firstTimer: fd.get('first_timer') === 'on',
      dateOfFirstVisit: str('date_of_first_visit') ?? undefined,
      notes: str('notes') ?? undefined,
    }

    try {
      const created = await createSatsangi(payload)
      setSuccess(`Registered! Satsangi ID: ${created.satsangiId}`)
      formRef.current?.reset()
    } catch {
      setError('Failed to register. Please check your details and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-6">
        <button
          type="button"
          onClick={() => navigate('/search')}
          className="mb-3 flex items-center gap-1.5 text-[13px] font-medium text-gray-400 hover:text-gray-600 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Search
        </button>
        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Add New Devotee</h1>
        <p className="mt-1 text-sm text-gray-500">Fill in all required fields to add a new devotee</p>
      </div>

      <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
          {/* Alerts */}
          {error && (
            <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3.5 text-sm text-red-700 animate-in fade-in">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-500" />
              {error}
            </div>
          )}
          {success && (
            <div className="flex items-center gap-3 rounded-xl border border-green-200 bg-green-50 px-4 py-3.5 text-sm text-green-700 font-medium animate-in fade-in">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
              {success}
            </div>
          )}

          {/* Section 1: Personal Details */}
          <CollapsibleSection
            title="Personal Details"
            icon={<User className="h-4 w-4" />}
            defaultOpen
          >
            <Row>
              <FormInput label="First Name" name="first_name" required placeholder="Enter first name" />
              <FormInput label="Last Name" name="last_name" required placeholder="Enter last name" />
            </Row>
            <Row>
              <FormInput label="Phone Number" name="phone_number" type="tel" required placeholder="+91 98765 43210" icon={<Phone className="h-4 w-4" />} />
              <FormInput label="Age" name="age" type="number" placeholder="e.g. 35" />
            </Row>
            <Row>
              <FormInput label="Date of Birth" name="date_of_birth" type="date" icon={<Calendar className="h-4 w-4" />} />
              <FormInput label="PAN" name="pan" placeholder="ABCDE1234F" icon={<CreditCard className="h-4 w-4" />} />
            </Row>
            <Row>
              <FormSelect label="Gender" name="gender" options={GENDERS} />
              <FormSelect label="Special Category" name="special_category" options={SPECIAL_CATEGORIES} />
            </Row>
            <Row>
              <FormSelect label="Nationality" name="nationality" options={NATIONALITIES} defaultValue="Indian" required />
              <FormInput label="Nick Name" name="nick_name" placeholder="Optional nickname" />
            </Row>

            {/* Govt ID sub-section */}
            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 space-y-4">
              <div className="flex items-center gap-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <Shield className="h-3.5 w-3.5" />
                Government ID
              </div>
              <Row>
                <FormSelect label="ID Type" name="govt_id_type" options={GOVT_ID_TYPES} />
                <FormInput label="ID Number" name="govt_id_number" placeholder="Enter ID number" />
              </Row>
              <Row>
                <FormInput label="ID Expiry Date" name="id_expiry_date" type="date" />
                <FormSelect label="Issuing Country" name="id_issuing_country" options={COUNTRIES} />
              </Row>
            </div>

            <Row>
              <FormInput label="Introducer" name="introducer" placeholder="Search by name…" />
              <FormCheckbox label="Print on Card" name="print_on_card" />
            </Row>
          </CollapsibleSection>

          {/* Section 2: Address Details */}
          <CollapsibleSection
            title="Address Details"
            icon={<MapPin className="h-4 w-4" />}
          >
            <Row>
              <FormSelect label="Country" name="country" options={COUNTRIES} defaultValue="India" required />
              <FormSelect label="State" name="state" options={INDIAN_STATES} />
            </Row>
            <FormInput label="Street Address" name="address" placeholder="e.g. 271, Sample Apartments, Sec-X" multiline icon={<MapPin className="h-4 w-4" />} />
            <Row>
              <FormInput label="City / Town" name="city" placeholder="Enter city" />
              <FormInput label="District" name="district" placeholder="Enter district" />
            </Row>
            <Row>
              <FormInput label="Pincode" name="pincode" placeholder="e.g. 201010" />
              <div />
            </Row>
          </CollapsibleSection>

          {/* Section 3: Other Details */}
          <CollapsibleSection
            title="Other Details"
            icon={<Settings className="h-4 w-4" />}
          >
            <Row>
              <FormInput label="Emergency Contact" name="emergency_contact" type="tel" placeholder="+91 98765 43210" icon={<Phone className="h-4 w-4" />} />
              <FormInput label="Ex-center Satsangi ID" name="ex_center_satsangi_id" placeholder="Enter ID if available" />
            </Row>
            <FormRadioGroup label="Introduced by" name="introduced_by" options={INTRODUCED_BY} />
            <Row>
              <FormInput label="Email" name="email" type="email" placeholder="user@example.com" icon={<Globe className="h-4 w-4" />} />
              <FormInput label="Date of First Visit" name="date_of_first_visit" type="date" icon={<Calendar className="h-4 w-4" />} />
            </Row>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <FormCheckbox label="Has Room in Ashram" name="has_room_in_ashram" />
              <FormCheckbox label="First Timer" name="first_timer" />
              <FormCheckbox label="Banned" name="banned" danger />
            </div>
            <FormInput label="Notes" name="notes" multiline placeholder="Any additional notes…" />
          </CollapsibleSection>

          {/* Submit row */}
          <div className="flex gap-3 pt-3">
            <button
              type="button"
              onClick={() => navigate('/search')}
              className={clsx(
                'rounded-xl border border-gray-200 bg-white px-6 py-3 text-sm font-semibold text-gray-600',
                'hover:bg-gray-50 hover:border-gray-300 transition-all duration-200',
              )}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={clsx(
                'flex-1 flex items-center justify-center gap-2.5 rounded-xl px-6 py-3 text-sm font-semibold text-white',
                'bg-brand-600 hover:bg-brand-700 active:bg-brand-800',
                'shadow-sm shadow-brand-600/25 hover:shadow-md hover:shadow-brand-600/30',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                'transition-all duration-200',
              )}
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Register Satsangi
                </>
              )}
            </button>
          </div>
      </form>
    </div>
  )
}

function Row({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">{children}</div>
}
