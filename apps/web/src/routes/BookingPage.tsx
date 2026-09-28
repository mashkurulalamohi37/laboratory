import { useEffect, useState } from "react";
import { unwrap } from "@nirnoy/api-client";
import { useAuth, useCart } from "@nirnoy/app-core";
import { useTranslation } from "@nirnoy/i18n";
import { Alert, Badge, Button, Card, Input, toast } from "@nirnoy/ui";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  Calendar,
  CheckCircle2,
  CreditCard,
  Home,
  Lock,
  Plus,
  ShieldCheck,
  TestTube2,
  User,
} from "lucide-react";
import { Link, useNavigate } from "react-router";
import { app } from "../api";

export default function BookingPage() {
  const { i18n } = useTranslation();
  const { status } = useAuth();
  const navigate = useNavigate();
  const isBn = i18n.language === "bn";

  const {
    items,
    itemCount,
    subtotal,
    mode,
    setMode,
    selectedCentreId,
    setSelectedCentreId,
    selectedAddressId,
    setSelectedAddressId,
    selectedSlotId,
    setSelectedSlotId,
    couponCode,
    setCouponCode,
    assignAllPatients,
    clearCart,
  } = useCart();

  const [step, setStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);

  // Data state
  const [patients, setPatients] = useState<any[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [addresses, setAddresses] = useState<any[]>([]);
  const [centres, setCentres] = useState<any[]>([]);
  const [slots, setSlots] = useState<any[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split("T")[0]!;
  });

  // New family member form state
  const [showAddFamily, setShowAddFamily] = useState<boolean>(false);
  const [familyForm, setFamilyForm] = useState({
    full_name: "",
    dob: "1995-01-01",
    sex: "M",
    relationship: "CHILD",
  });

  // New address form state
  const [showAddAddress, setShowAddAddress] = useState<boolean>(false);
  const [addressForm, setAddressForm] = useState({
    house: "",
    road: "",
    block: "",
    landmark: "",
  });

  // Quote State
  const [couponInput, setCouponInput] = useState<string>("");
  const [quote, setQuote] = useState<{
    subtotal: number;
    discount: number;
    collection_fee: number;
    total: number;
    coupon_applied: string | null;
  }>({
    subtotal,
    discount: 0,
    collection_fee: mode === "HOME" ? (subtotal >= 200000 ? 0 : 15000) : 0,
    total: subtotal + (mode === "HOME" && subtotal < 200000 ? 15000 : 0),
    coupon_applied: null,
  });

  // Payment Selection
  const [paymentMethod, setPaymentMethod] = useState<"CASH" | "ONLINE">("ONLINE");
  const [confirmedBooking, setConfirmedBooking] = useState<any | null>(null);

  const formatTk = (poisha: number) => `৳${Math.round(poisha / 100).toLocaleString()}`;

  // Require auth or redirect
  useEffect(() => {
    if (status === "anonymous") {
      navigate(`/login?next=${encodeURIComponent("/book")}`);
    }
  }, [status, navigate]);

  // Load patient profiles and addresses
  useEffect(() => {
    async function loadData() {
      if (status !== "authenticated") return;
      try {
        const [pRes, fRes, aRes, cRes] = await Promise.all([
          unwrap(app.api.GET("/api/v1/patients/me")),
          unwrap(app.api.GET("/api/v1/patients/family")),
          unwrap(app.api.GET("/api/v1/addresses")),
          unwrap(app.api.GET("/api/v1/centres")),
        ]);

        const allPatients: any[] = [];
        if (pRes) {
          allPatients.push({ ...pRes, isSelf: true });
        }
        if (fRes) {
          fRes.forEach((f: any) => {
            allPatients.push({ ...f.patient, relationship: f.relationship });
          });
        }
        setPatients(allPatients);
        if (allPatients.length > 0 && !selectedPatientId) {
          const firstP = allPatients[0];
          setSelectedPatientId(firstP.id);
          assignAllPatients(firstP.id, firstP.full_name);
        }

        if (aRes && aRes.length > 0) {
          setAddresses(aRes);
          if (!selectedAddressId && aRes[0]) {
            setSelectedAddressId(aRes[0].id);
          }
        }

        if (cRes && cRes.length > 0) {
          setCentres(cRes);
          if (!selectedCentreId && cRes[0]) {
            setSelectedCentreId(cRes[0].id);
          }
        }
      } catch {
        // Fallback demo state
        const dummyPatient = {
          id: "00000000-0000-0000-0000-000000000001",
          patient_code: "PT-2026-000001",
          full_name: "Account Holder",
          isSelf: true,
        };
        setPatients([dummyPatient]);
        setSelectedPatientId(dummyPatient.id);
        assignAllPatients(dummyPatient.id, dummyPatient.full_name);

        const dummyAddress = {
          id: "00000000-0000-0000-0000-000000000002",
          house: "House 14, Road 5",
          road: "Dhanmondi",
          label: "HOME",
        };
        setAddresses([dummyAddress]);
        setSelectedAddressId(dummyAddress.id);

        const dummyCentre = {
          id: "00000000-0000-0000-0000-000000000003",
          name: "Dhanmondi Central Diagnostic Centre",
          address: "Road 7/A, Dhanmondi, Dhaka",
        };
        setCentres([dummyCentre]);
        setSelectedCentreId(dummyCentre.id);
      }
    }
    loadData();
  }, [status]);

  // Load available slots
  useEffect(() => {
    async function loadSlots() {
      const ownerId = mode === "HOME" ? selectedAddressId : selectedCentreId;
      if (!ownerId) return;

      try {
        const data = await unwrap(
          app.api.GET("/api/v1/slots/available", {
            params: {
              query: {
                owner_type: mode === "HOME" ? "ZONE" : "CENTRE",
                owner_id: ownerId,
                from_date: selectedDate,
                to_date: selectedDate,
                mode,
              },
            },
          }),
        );
        if (data && data.length > 0) {
          setSlots(data);
          if (!selectedSlotId && data[0]) {
            setSelectedSlotId(data[0].id);
          }
        }
      } catch {
        // Fallback slots
        const demoSlots = [
          { id: "slot-1", start_time: "08:00:00", end_time: "10:00:00", available: 5 },
          { id: "slot-2", start_time: "10:00:00", end_time: "12:00:00", available: 8 },
          { id: "slot-3", start_time: "14:00:00", end_time: "16:00:00", available: 4 },
          { id: "slot-4", start_time: "16:00:00", end_time: "18:00:00", available: 6 },
        ];
        setSlots(demoSlots);
        if (!selectedSlotId && demoSlots[0]) setSelectedSlotId(demoSlots[0].id);
      }
    }
    loadSlots();
  }, [mode, selectedCentreId, selectedAddressId, selectedDate]);

  // Refresh Quote calculation
  useEffect(() => {
    async function fetchQuote() {
      if (items.length === 0 || !selectedPatientId) return;
      try {
        const payloadItems = items.map((i) => ({
          patient_id: i.patientId || selectedPatientId,
          item_type: i.type,
          item_id: i.id,
        }));

        const data = await unwrap(
          app.api.POST("/api/v1/bookings/quote", {
            body: {
              mode,
              centre_id: mode === "CENTRE" ? selectedCentreId || undefined : undefined,
              address_id: mode === "HOME" ? selectedAddressId || undefined : undefined,
              items: payloadItems,
              coupon_code: couponCode || undefined,
            },
          }),
        );
        if (data) {
          setQuote({
            subtotal: data.subtotal,
            discount: data.discount,
            collection_fee: data.collection_fee,
            total: data.total,
            coupon_applied: data.coupon_applied ?? null,
          });
        }
      } catch {
        // Fallback calculation
        const fee = mode === "HOME" ? (subtotal >= 200000 ? 0 : 15000) : 0;
        setQuote({
          subtotal,
          discount: 0,
          collection_fee: fee,
          total: subtotal + fee,
          coupon_applied: null,
        });
      }
    }
    fetchQuote();
  }, [items, mode, selectedCentreId, selectedAddressId, couponCode, subtotal, selectedPatientId]);

  // Handle Add Family Member
  const handleAddFamily = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!familyForm.full_name) return;
    setLoading(true);
    try {
      const newMember = await unwrap(
        app.api.POST("/api/v1/patients/family", {
          body: {
            full_name: familyForm.full_name,
            dob: familyForm.dob,
            sex: familyForm.sex as any,
            relationship: familyForm.relationship as any,
          },
        }),
      );
      if (newMember) {
        setPatients((prev) => [...prev, { ...newMember.patient, relationship: newMember.relationship }]);
        setSelectedPatientId(newMember.patient_id);
        assignAllPatients(newMember.patient_id, newMember.patient.full_name);
        setShowAddFamily(false);
        setFamilyForm({ full_name: "", dob: "1995-01-01", sex: "M", relationship: "CHILD" });
        toast.success("Family member added successfully");
      }
    } catch {
      toast.error("Failed to add family member");
    } finally {
      setLoading(false);
    }
  };

  // Handle Add Address
  const handleCreateAddress = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addressForm.house) return;
    setLoading(true);
    try {
      const newAddr = await unwrap(
        app.api.POST("/api/v1/addresses", {
          body: {
            house: addressForm.house,
            road: addressForm.road || undefined,
            block: addressForm.block || undefined,
            landmark: addressForm.landmark || undefined,
            label: "HOME",
            is_default: false,
          },
        }),
      );
      if (newAddr) {
        setAddresses((prev) => [...prev, newAddr]);
        setSelectedAddressId(newAddr.id);
        setShowAddAddress(false);
        setAddressForm({ house: "", road: "", block: "", landmark: "" });
        toast.success("Address added successfully");
      }
    } catch {
      toast.error("Failed to add address");
    } finally {
      setLoading(false);
    }
  };

  // Handle Coupon Apply
  const handleApplyCoupon = () => {
    if (!couponInput.trim()) return;
    setCouponCode(couponInput.trim().toUpperCase());
    toast.success("Coupon code submitted");
  };

  // Confirm and Submit Booking
  const handleConfirmBooking = async () => {
    if (!selectedPatientId || !selectedSlotId) {
      toast.error("Please complete all patient and time slot selections.");
      return;
    }
    setLoading(true);
    try {
      const payloadItems = items.map((i) => ({
        patient_id: i.patientId || selectedPatientId,
        item_type: i.type,
        item_id: i.id,
      }));

      const res = await unwrap(
        app.api.POST("/api/v1/bookings", {
          body: {
            mode,
            centre_id: mode === "CENTRE" ? selectedCentreId || undefined : undefined,
            address_id: mode === "HOME" ? selectedAddressId || undefined : undefined,
            slot_id: selectedSlotId,
            items: payloadItems,
            coupon_code: couponCode || undefined,
          },
        }),
      );

      if (res) {
        setConfirmedBooking(res);
        clearCart();
        toast.success("Booking confirmed successfully!");
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to confirm booking.");
    } finally {
      setLoading(false);
    }
  };

  // If cart is empty and not confirmed
  if (itemCount === 0 && !confirmedBooking) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-20 text-center">
        <div className="size-16 rounded-2xl bg-brand-50 flex items-center justify-center text-brand-600 mx-auto mb-4">
          <TestTube2 className="size-8" />
        </div>
        <h2 className="text-2xl font-bold text-fg">Your diagnostic cart is empty</h2>
        <p className="text-muted text-sm mt-2 max-w-md mx-auto">
          Please explore our catalog of diagnostic tests and preventive checkup packages to start your booking.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button asChild>
            <Link to="/tests">Browse Tests</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link to="/packages">Health Packages</Link>
          </Button>
        </div>
      </div>
    );
  }

  // If booking is confirmed: Show Success Screen
  if (confirmedBooking) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12">
        <Card className="p-8 text-center border-brand-300 bg-surface shadow-lg">
          <div className="size-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="size-10" />
          </div>

          <h1 className="text-2xl font-extrabold text-fg">Booking Confirmed!</h1>
          <p className="text-sm text-muted mt-1">
            Your appointment has been successfully scheduled.
          </p>

          <div className="mt-6 p-4 rounded-2xl bg-subtle/50 border border-border text-left space-y-3 font-mono text-sm">
            <div className="flex justify-between">
              <span className="text-muted">Booking Reference:</span>
              <span className="font-bold text-fg">{confirmedBooking.booking_number}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Scheduled Date:</span>
              <span className="text-fg">{confirmedBooking.slot_date}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Fulfillment:</span>
              <span className="text-fg">
                {confirmedBooking.fulfillment_type === "HOME_COLLECTION" ? "Home Collection" : "Lab Visit"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Total Amount:</span>
              <span className="font-bold text-brand-600">
                ৳{Number(confirmedBooking.total_amount).toLocaleString()}
              </span>
            </div>
          </div>

          <div className="mt-8 flex flex-col sm:flex-row justify-center gap-3">
            <Button asChild>
              <Link to="/account/bookings">View in Account</Link>
            </Button>
            <Button variant="secondary" asChild>
              <Link to="/">Back to Home</Link>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Stepper Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-muted mb-2">
          <span>Step {step} of 5</span>
          <span>
            {step === 1 && "Select Patient"}
            {step === 2 && "Collection Mode"}
            {step === 3 && "Date & Time"}
            {step === 4 && "Review & Promo"}
            {step === 5 && "Payment"}
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-border overflow-hidden">
          <div
            className="h-full bg-brand transition-all duration-300"
            style={{ width: `${(step / 5) * 100}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Main Step Body: 2 cols */}
        <div className="lg:col-span-2 space-y-6">
          {/* STEP 1: PATIENT SELECTION */}
          {step === 1 && (
            <Card className="p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-fg flex items-center gap-2">
                    <User className="size-5 text-brand" />
                    <span>{isBn ? "রোগী নির্বাচন করুন" : "Select Patient for Tests"}</span>
                  </h2>
                  <p className="text-xs text-muted mt-0.5">
                    {isBn
                      ? "কার জন্য টেস্ট বুক করছেন তা বেছে নিন অথবা নতুন সদস্য যোগ করুন।"
                      : "Choose the patient record or add a family member for accurate reportage."}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setShowAddFamily(!showAddFamily)}
                >
                  <Plus className="size-4 mr-1" />
                  <span>{showAddFamily ? "Close" : "+ Add Member"}</span>
                </Button>
              </div>

              {/* Add Family Form */}
              {showAddFamily && (
                <form
                  onSubmit={handleAddFamily}
                  className="p-4 rounded-2xl bg-brand-50/40 border border-brand-200 space-y-4"
                >
                  <h4 className="font-bold text-sm text-fg">Add New Family Member</h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-muted block mb-1">Full Name</label>
                      <Input
                        value={familyForm.full_name}
                        onChange={(e) => setFamilyForm({ ...familyForm, full_name: e.target.value })}
                        placeholder="e.g. Ayesha Rahman"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted block mb-1">Date of Birth</label>
                      <Input
                        type="date"
                        value={familyForm.dob}
                        onChange={(e) => setFamilyForm({ ...familyForm, dob: e.target.value })}
                        required
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-muted block mb-1">Gender</label>
                      <select
                        value={familyForm.sex}
                        onChange={(e) => setFamilyForm({ ...familyForm, sex: e.target.value })}
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-fg shadow-sm"
                      >
                        <option value="M">Male</option>
                        <option value="F">Female</option>
                        <option value="O">Other</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-muted block mb-1">Relationship</label>
                      <select
                        value={familyForm.relationship}
                        onChange={(e) => setFamilyForm({ ...familyForm, relationship: e.target.value })}
                        className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-fg shadow-sm"
                      >
                        <option value="SPOUSE">Spouse</option>
                        <option value="CHILD">Child</option>
                        <option value="PARENT">Parent</option>
                        <option value="SIBLING">Sibling</option>
                        <option value="OTHER">Other</option>
                      </select>
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <Button type="button" variant="ghost" size="sm" onClick={() => setShowAddFamily(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" size="sm" disabled={loading}>
                      Save Member
                    </Button>
                  </div>
                </form>
              )}

              {/* Patient List */}
              <div className="space-y-3">
                {patients.map((p) => {
                  const isSelected = selectedPatientId === p.id;
                  return (
                    <div
                      key={p.id}
                      onClick={() => {
                        setSelectedPatientId(p.id);
                        assignAllPatients(p.id, p.full_name);
                      }}
                      className={`flex items-center justify-between p-4 rounded-2xl border-2 cursor-pointer transition ${
                        isSelected
                          ? "border-brand bg-brand-50/20 shadow-sm"
                          : "border-border hover:border-brand-200"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`size-10 rounded-full flex items-center justify-center font-bold text-sm ${
                            isSelected ? "bg-brand text-white" : "bg-surface-muted text-muted"
                          }`}
                        >
                          {p.full_name?.charAt(0) || "P"}
                        </div>
                        <div>
                          <p className="font-bold text-fg text-sm">{p.full_name}</p>
                          <p className="text-xs text-muted">
                            {p.isSelf ? "Account Owner" : p.relationship || "Family Member"}
                          </p>
                        </div>
                      </div>
                      <input
                        type="radio"
                        checked={isSelected}
                        onChange={() => {}}
                        className="size-4 text-brand"
                      />
                    </div>
                  );
                })}
              </div>

              <div className="mt-6 flex justify-end">
                <Button size="lg" onClick={() => setStep(2)} disabled={!selectedPatientId}>
                  <span>{isBn ? "পরবর্তী ধাপ" : "Continue to Mode"}</span>
                  <ArrowRight className="size-4 ml-1.5" />
                </Button>
              </div>
            </Card>
          )}

          {/* STEP 2: COLLECTION MODE */}
          {step === 2 && (
            <Card className="p-6 space-y-6">
              <div>
                <h2 className="text-lg font-bold text-fg flex items-center gap-2">
                  <Home className="size-5 text-brand" />
                  <span>{isBn ? "স্যাম্পল সংগ্রহের মাধ্যম" : "Sample Collection Mode"}</span>
                </h2>
                <p className="text-xs text-muted mt-0.5">
                  {isBn
                    ? "বাসায় বসে স্যাম্পল কালেকশন চান নাকি সেন্টারে ভিজিট করবেন?"
                    : "Choose between convenient doorstep collection or walk-in lab visit."}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div
                  onClick={() => setMode("HOME")}
                  className={`p-5 rounded-2xl border-2 cursor-pointer transition flex flex-col justify-between ${
                    mode === "HOME"
                      ? "border-brand bg-brand-50/20 shadow-sm"
                      : "border-border hover:border-brand-200"
                  }`}
                >
                  <div>
                    <div className="size-10 rounded-xl bg-brand-50 text-brand flex items-center justify-center mb-3">
                      <Home className="size-5" />
                    </div>
                    <h3 className="font-bold text-fg text-base">{isBn ? "হোম কালেকশন" : "Home Collection"}</h3>
                    <p className="text-xs text-muted mt-1 leading-relaxed">
                      {isBn
                        ? "আমাদের অভিজ্ঞ প্যাথলজিস্ট বাসায় এসে স্যাম্পল সংগ্রহ করবেন।"
                        : "Certified phlebotomist arrives at your home with sterile vacutainer tubes."}
                    </p>
                  </div>
                  <Badge tone="success" className="mt-4 self-start text-xs">
                    {subtotal >= 200000 ? (isBn ? "ফ্রি ডেলিভারি" : "FREE above ৳2,000") : "৳150 Fee"}
                  </Badge>
                </div>

                <div
                  onClick={() => setMode("CENTRE")}
                  className={`p-5 rounded-2xl border-2 cursor-pointer transition flex flex-col justify-between ${
                    mode === "CENTRE"
                      ? "border-brand bg-brand-50/20 shadow-sm"
                      : "border-border hover:border-brand-200"
                  }`}
                >
                  <div>
                    <div className="size-10 rounded-xl bg-brand-50 text-brand flex items-center justify-center mb-3">
                      <Building2 className="size-5" />
                    </div>
                    <h3 className="font-bold text-fg text-base">{isBn ? "সেন্টার ভিজিট" : "Centre Visit"}</h3>
                    <p className="text-xs text-muted mt-1 leading-relaxed">
                      {isBn
                        ? "আপনার নিকটস্থ ডায়াগনস্টিক সেন্টারে গিয়ে দ্রুত স্যাম্পল জমা দিন।"
                        : "Walk into any of our premier diagnostic hubs at your scheduled time."}
                    </p>
                  </div>
                  <Badge tone="neutral" className="mt-4 self-start text-xs">
                    {isBn ? "কোনো অতিরিক্ত ফি নেই" : "No Collection Fee"}
                  </Badge>
                </div>
              </div>

              {/* Address Picker for Home mode */}
              {mode === "HOME" && (
                <div className="pt-4 border-t border-border space-y-3">
                  <div className="flex justify-between items-center">
                    <label className="text-sm font-bold text-fg">{isBn ? "কালেকশন ঠিকানা" : "Select Collection Address"}</label>
                    <Button size="sm" variant="secondary" onClick={() => setShowAddAddress(!showAddAddress)}>
                      <Plus className="size-4 mr-1" />
                      <span>{isBn ? "নতুন ঠিকানা" : "+ Add Address"}</span>
                    </Button>
                  </div>

                  {showAddAddress && (
                    <form onSubmit={handleCreateAddress} className="p-4 rounded-xl bg-brand-50/30 border border-brand-200 space-y-3">
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs text-muted block mb-1">House / Flat No.</label>
                          <Input
                            value={addressForm.house}
                            onChange={(e) => setAddressForm({ ...addressForm, house: e.target.value })}
                            placeholder="e.g. House 12, Flat 4B"
                            required
                          />
                        </div>
                        <div>
                          <label className="text-xs text-muted block mb-1">Road / Street</label>
                          <Input
                            value={addressForm.road}
                            onChange={(e) => setAddressForm({ ...addressForm, road: e.target.value })}
                            placeholder="e.g. Road 7/A, Dhanmondi"
                          />
                        </div>
                      </div>
                      <div className="flex justify-end gap-2 pt-2">
                        <Button type="button" variant="ghost" size="sm" onClick={() => setShowAddAddress(false)}>
                          Cancel
                        </Button>
                        <Button type="submit" size="sm" disabled={loading}>
                          Save Address
                        </Button>
                      </div>
                    </form>
                  )}

                  <div className="space-y-2">
                    {addresses.map((a) => (
                      <label
                        key={a.id}
                        className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition ${
                          selectedAddressId === a.id ? "border-brand bg-brand-50/20" : "border-border"
                        }`}
                      >
                        <input
                          type="radio"
                          name="address_select"
                          checked={selectedAddressId === a.id}
                          onChange={() => setSelectedAddressId(a.id)}
                          className="mt-1 size-4 text-brand"
                        />
                        <div>
                          <p className="font-semibold text-fg text-sm">{a.house}, {a.road}</p>
                          <p className="text-xs text-muted capitalize">{a.label}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Centre Picker for Centre mode */}
              {mode === "CENTRE" && (
                <div className="pt-4 border-t border-border space-y-3">
                  <label className="text-sm font-bold text-fg">{isBn ? "সেন্টার নির্বাচন করুন" : "Select Centre Branch"}</label>
                  <div className="space-y-2">
                    {centres.map((c) => (
                      <label
                        key={c.id}
                        className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition ${
                          selectedCentreId === c.id ? "border-brand bg-brand-50/20" : "border-border"
                        }`}
                      >
                        <input
                          type="radio"
                          name="centre_select"
                          checked={selectedCentreId === c.id}
                          onChange={() => setSelectedCentreId(c.id)}
                          className="mt-1 size-4 text-brand"
                        />
                        <div>
                          <p className="font-semibold text-fg text-sm">{isBn && c.name_bn ? c.name_bn : c.name}</p>
                          <p className="text-xs text-muted">{c.address}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-6 flex justify-between">
                <Button variant="secondary" size="lg" onClick={() => setStep(1)}>
                  <ArrowLeft className="size-4 mr-1.5" />
                  <span>{isBn ? "পূর্ববর্তী" : "Back"}</span>
                </Button>
                <Button size="lg" onClick={() => setStep(3)}>
                  <span>{isBn ? "সময়সূচী নির্বাচন" : "Continue to Slot Picker"}</span>
                  <ArrowRight className="size-4 ml-1.5" />
                </Button>
              </div>
            </Card>
          )}

          {/* STEP 3: DATE & TIME SLOT PICKER */}
          {step === 3 && (
            <Card className="p-6 space-y-6">
              <div>
                <h2 className="text-lg font-bold text-fg flex items-center gap-2">
                  <Calendar className="size-5 text-brand" />
                  <span>{isBn ? "তারিখ ও সময়সূচী" : "Appointment Date & Time"}</span>
                </h2>
                <p className="text-xs text-muted mt-0.5">
                  {isBn
                    ? "আপনার সুবিধাজনক সংগ্রহের তারিখ ও সময় নির্বাচন করুন।"
                    : "Select your preferred date and collection time window."}
                </p>
              </div>

              <div>
                <label className="text-xs font-bold text-muted block mb-2">{isBn ? "তারিখ নির্বাচন করুন" : "Select Date"}</label>
                <input
                  type="date"
                  value={selectedDate}
                  min={new Date().toISOString().split("T")[0]}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-fg shadow-sm focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-muted block mb-3">{isBn ? "উপলব্ধ সময়সূচী (Slots)" : "Available Time Slots"}</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {slots.map((s) => {
                    const isSelected = selectedSlotId === s.id;
                    const formatTime = (tStr: string) => {
                      const [h] = tStr.split(":");
                      const hour = parseInt(h!, 10);
                      const ampm = hour >= 12 ? "PM" : "AM";
                      const h12 = hour % 12 || 12;
                      return `${h12}:00 ${ampm}`;
                    };
                    const timeLabel = `${formatTime(s.start_time)} – ${formatTime(s.end_time)}`;

                    return (
                      <div
                        key={s.id}
                        onClick={() => setSelectedSlotId(s.id)}
                        className={`p-3.5 rounded-xl border text-center cursor-pointer transition ${
                          isSelected
                            ? "border-brand bg-brand text-white font-bold shadow-md"
                            : "border-border bg-surface hover:border-brand-300 text-fg"
                        }`}
                      >
                        <p className="text-xs">{timeLabel}</p>
                        <p className={`text-[11px] mt-1 ${isSelected ? "text-white/80" : "text-muted"}`}>
                          {s.available} {isBn ? "স্লট বাকি" : "slots left"}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="mt-6 flex justify-between">
                <Button variant="secondary" size="lg" onClick={() => setStep(2)}>
                  <ArrowLeft className="size-4 mr-1.5" />
                  <span>{isBn ? "পূর্ববর্তী" : "Back"}</span>
                </Button>
                <Button size="lg" onClick={() => setStep(4)} disabled={!selectedSlotId}>
                  <span>{isBn ? "অর্ডার রিভিউ" : "Review Summary"}</span>
                  <ArrowRight className="size-4 ml-1.5" />
                </Button>
              </div>
            </Card>
          )}

          {/* STEP 4: ORDER REVIEW & COUPON */}
          {step === 4 && (
            <Card className="p-6 space-y-6">
              <div>
                <h2 className="text-lg font-bold text-fg flex items-center gap-2">
                  <CheckCircle2 className="size-5 text-brand" />
                  <span>{isBn ? "অর্ডার বিবরণী ও কুপন" : "Review Order & Apply Coupon"}</span>
                </h2>
                <p className="text-xs text-muted mt-0.5">
                  {isBn ? "আপনার নির্বাচিত টেস্টসমূহ এবং সর্বমোট মূল্য পরীক্ষা করুন।" : "Confirm your items and enter promo discounts."}
                </p>
              </div>

              <div className="divide-y divide-border border rounded-xl overflow-hidden">
                {items.map((item) => (
                  <div key={item.id} className="p-4 flex items-center justify-between bg-surface">
                    <div>
                      <p className="font-bold text-fg text-sm">{item.name}</p>
                      <p className="text-xs text-muted">{item.type === "PACKAGE" ? "Health Package" : "Diagnostic Test"}</p>
                    </div>
                    <span className="font-bold text-brand">{formatTk(item.price)}</span>
                  </div>
                ))}
              </div>

              {/* Coupon input */}
              <div className="flex gap-2">
                <Input
                  value={couponInput}
                  onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                  placeholder={isBn ? "কুপন কোড (যেমন: WELCOME10)" : "Promo Code (e.g. WELCOME10)"}
                  className="uppercase font-mono text-sm"
                />
                <Button variant="secondary" onClick={handleApplyCoupon}>
                  {isBn ? "প্রয়োগ করুন" : "Apply"}
                </Button>
              </div>

              {quote.coupon_applied && (
                <Alert tone="success" className="text-xs">
                  ✓ Coupon <strong>{quote.coupon_applied}</strong> applied! You saved {formatTk(quote.discount)}.
                </Alert>
              )}

              <div className="mt-6 flex justify-between">
                <Button variant="secondary" size="lg" onClick={() => setStep(3)}>
                  <ArrowLeft className="size-4 mr-1.5" />
                  <span>{isBn ? "পূর্ববর্তী" : "Back"}</span>
                </Button>
                <Button size="lg" onClick={() => setStep(5)}>
                  <span>{isBn ? "পেমেন্ট নির্বাচন" : "Proceed to Payment"}</span>
                  <ArrowRight className="size-4 ml-1.5" />
                </Button>
              </div>
            </Card>
          )}

          {/* STEP 5: PAYMENT SELECTION */}
          {step === 5 && (
            <Card className="p-6 space-y-6">
              <div>
                <h2 className="text-lg font-bold text-fg flex items-center gap-2">
                  <CreditCard className="size-5 text-brand" />
                  <span>{isBn ? "পেমেন্ট পদ্ধতি নির্বাচন" : "Select Payment Method"}</span>
                </h2>
                <p className="text-xs text-muted mt-0.5">
                  {isBn ? "অনলাইনে নিরাপদ পেমেন্ট করুন অথবা স্যাম্পল কালেকশনের সময় ক্যাশ দিন।" : "Pay securely online via SSLCommerz or Cash on Collection."}
                </p>
              </div>

              <div className="space-y-3">
                <label
                  className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition ${
                    paymentMethod === "ONLINE" ? "border-brand bg-brand-50/20 shadow-sm" : "border-border"
                  }`}
                >
                  <input
                    type="radio"
                    name="payment_method"
                    checked={paymentMethod === "ONLINE"}
                    onChange={() => setPaymentMethod("ONLINE")}
                    className="mt-1 size-4 text-brand"
                  />
                  <div>
                    <p className="font-bold text-fg text-sm">{isBn ? "অনলাইন পেমেন্ট (SSLCommerz Gateway)" : "Online Payment (bKash / Nagad / Cards)"}</p>
                    <p className="text-xs text-muted mt-0.5">
                      {isBn ? "বিকাশ, নগদ, রকেট ও ভিসা/মাস্টারকার্ডের মাধ্যমে নিরাপদ পেমেন্ট।" : "Instant online payment via bKash, Nagad, Visa, Mastercard, and Internet Banking."}
                    </p>
                  </div>
                </label>

                <label
                  className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition ${
                    paymentMethod === "CASH" ? "border-brand bg-brand-50/20 shadow-sm" : "border-border"
                  }`}
                >
                  <input
                    type="radio"
                    name="payment_method"
                    checked={paymentMethod === "CASH"}
                    onChange={() => setPaymentMethod("CASH")}
                    className="mt-1 size-4 text-brand"
                  />
                  <div>
                    <p className="font-bold text-fg text-sm">{isBn ? "ক্যাশ অন কালেকশন (Cash on Collection)" : "Cash on Collection"}</p>
                    <p className="text-xs text-muted mt-0.5">
                      {isBn ? "স্যাম্পল সংগ্রহের সময় স্বাস্থ্যকর্মীকে ক্যাশ মূল্য পরিশোধ করুন।" : "Pay in cash to our medical collector upon sample collection at home."}
                    </p>
                  </div>
                </label>
              </div>

              <div className="mt-6 flex justify-between">
                <Button variant="secondary" size="lg" onClick={() => setStep(4)}>
                  <ArrowLeft className="size-4 mr-1.5" />
                  <span>{isBn ? "পূর্ববর্তী" : "Back"}</span>
                </Button>
                <Button size="lg" onClick={handleConfirmBooking} disabled={loading}>
                  <Lock className="size-4 mr-1.5" />
                  <span>{loading ? (isBn ? "প্রক্রিয়াধীন..." : "Processing...") : isBn ? "বুকিং নিশ্চিত করুন" : "Confirm & Book Now"}</span>
                </Button>
              </div>
            </Card>
          )}
        </div>

        {/* Right Sticky Summary Sidebar */}
        <Card className="p-6 sticky top-24 border-border shadow-md bg-surface space-y-4">
          <h3 className="font-bold text-fg text-base border-b border-border pb-3">
            {isBn ? "বুকিং সামারি" : "Order Summary"}
          </h3>

          <div className="space-y-2.5 text-sm">
            <div className="flex justify-between text-muted">
              <span>{isBn ? "আইটেম সাবটোটাল" : "Subtotal"}</span>
              <span className="font-semibold text-fg">{formatTk(quote.subtotal)}</span>
            </div>

            {quote.discount > 0 && (
              <div className="flex justify-between text-emerald-600 font-medium">
                <span>{isBn ? "কুপন ছাড়" : "Discount"}</span>
                <span>- {formatTk(quote.discount)}</span>
              </div>
            )}

            <div className="flex justify-between text-muted">
              <span>{isBn ? "কালেকশন ফি" : "Collection Fee"}</span>
              <span>
                {quote.collection_fee === 0 ? (
                  <span className="text-emerald-600 font-bold">{isBn ? "ফ্রি" : "FREE"}</span>
                ) : (
                  formatTk(quote.collection_fee)
                )}
              </span>
            </div>

            <div className="pt-3 border-t border-border flex justify-between items-baseline">
              <span className="font-bold text-fg text-base">{isBn ? "সর্বমোট প্রদেয়" : "Total Payable"}</span>
              <span className="text-2xl font-extrabold text-brand">
                {formatTk(quote.total)}
              </span>
            </div>
          </div>

          <div className="pt-3 border-t border-border/60 text-xs text-muted space-y-2">
            <p className="flex items-center gap-1.5 text-emerald-700 font-medium">
              <ShieldCheck className="size-4" />
              <span>{isBn ? "১০০% নিরাপদ ও এনক্রিপ্টেড বুকিং" : "100% Secure & Confidential"}</span>
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
