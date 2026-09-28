import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  LoadingRows,
  Select,
  toast,
} from "@nirnoy/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Users } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";

interface AddFamilyFormData {
  full_name: string;
  relationship: "SPOUSE" | "CHILD" | "FATHER" | "MOTHER" | "SIBLING" | "OTHER";
  sex: "M" | "F" | "O";
  dob: string;
  phone?: string;
  blood_group?: string;
}

export default function FamilyMembersPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);

  const {
    data: familyMembers,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["family-members"],
    queryFn: () => unwrap(api.GET("/api/v1/patients/family")),
  });

  const form = useForm<AddFamilyFormData>({
    defaultValues: {
      full_name: "",
      relationship: "SPOUSE",
      sex: "F",
      dob: "1990-01-01",
      phone: "",
      blood_group: "",
    },
  });

  const addMutation = useMutation({
    mutationFn: (data: AddFamilyFormData) =>
      unwrap(
        api.POST("/api/v1/patients/family", {
          body: {
            full_name: data.full_name,
            relationship: data.relationship,
            sex: data.sex,
            dob: data.dob,
            phone: data.phone || undefined,
            blood_group: (data.blood_group || undefined) as any,
          },
        }),
      ),
    onSuccess: () => {
      toast.success("Family member added successfully");
      setShowAddForm(false);
      form.reset();
      void queryClient.invalidateQueries({ queryKey: ["family-members"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to add family member");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (patientId: string) =>
      unwrap(
        api.DELETE("/api/v1/patients/family/{patient_id}", {
          params: { path: { patient_id: patientId } },
        }),
      ),
    onSuccess: () => {
      toast.success("Family member removed");
      void queryClient.invalidateQueries({ queryKey: ["family-members"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to remove member");
    },
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:py-12">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted">
            <Link to="/account" className="hover:underline">
              Account
            </Link>
            <span>/</span>
            <span>Family Members</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Family & Dependents</h1>
          <p className="mt-1 text-sm text-muted">
            Add your parents, spouse, or children to book tests for them seamlessly.
          </p>
        </div>
        <Button
          onClick={() => setShowAddForm(!showAddForm)}
          variant={showAddForm ? "secondary" : "primary"}
        >
          <Plus className="size-4" />
          {showAddForm ? "Close Form" : "Add Member"}
        </Button>
      </div>

      {showAddForm && (
        <Card className="mb-8 border-brand/30 shadow-md">
          <CardHeader
            title="Add New Family Member"
            description="Enter patient details for accurate lab reports and reference ranges."
          />
          <CardBody>
            <form
              onSubmit={form.handleSubmit((d) => addMutation.mutate(d))}
              className="grid gap-4 sm:grid-cols-2"
            >
              <Field label="Full Name" required className="sm:col-span-2">
                <Input
                  placeholder="e.g. Ayesha Rahman"
                  {...form.register("full_name", { required: true })}
                />
              </Field>

              <Field label="Relationship" required>
                <Select {...form.register("relationship", { required: true })}>
                  <option value="SPOUSE">Spouse</option>
                  <option value="CHILD">Child</option>
                  <option value="FATHER">Father</option>
                  <option value="MOTHER">Mother</option>
                  <option value="SIBLING">Sibling</option>
                  <option value="OTHER">Other</option>
                </Select>
              </Field>

              <Field label="Gender" required>
                <Select {...form.register("sex", { required: true })}>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="O">Other</option>
                </Select>
              </Field>

              <Field label="Date of Birth" required>
                <Input type="date" {...form.register("dob", { required: true })} />
              </Field>

              <Field label="Blood Group (Optional)">
                <Select {...form.register("blood_group")}>
                  <option value="">Select...</option>
                  <option value="A+">A+</option>
                  <option value="A-">A-</option>
                  <option value="B+">B+</option>
                  <option value="B-">B-</option>
                  <option value="O+">O+</option>
                  <option value="O-">O-</option>
                  <option value="AB+">AB+</option>
                  <option value="AB-">AB-</option>
                </Select>
              </Field>

              <Field label="Phone Number (Optional)" className="sm:col-span-2">
                <Input placeholder="01XXXXXXXXX" {...form.register("phone")} />
              </Field>

              <div className="flex gap-2 sm:col-span-2">
                <Button type="submit" loading={addMutation.isPending}>
                  Save Member
                </Button>
                <Button variant="ghost" onClick={() => setShowAddForm(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      {isLoading ? (
        <LoadingRows rows={3} label="Loading family members..." />
      ) : isError ? (
        <Alert tone="danger">Failed to load family members.</Alert>
      ) : !familyMembers || familyMembers.length === 0 ? (
        <Card>
          <CardBody className="py-12 text-center">
            <Users className="mx-auto mb-3 size-12 text-muted" />
            <h3 className="text-lg font-bold text-foreground">No family members registered</h3>
            <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
              Add your family members so you can schedule health tests and track their records.
            </p>
            <Button className="mt-4" onClick={() => setShowAddForm(true)}>
              <Plus className="size-4" />
              Add First Member
            </Button>
          </CardBody>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {familyMembers.map((m: any) => (
            <Card interactive key={m.id} className="border border-border">
              <CardBody className="flex items-start justify-between p-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-foreground">
                      {m.patient?.full_name || m.full_name}
                    </span>
                    <Badge tone="brand">{m.relationship}</Badge>
                  </div>
                  <p className="text-xs text-muted">
                    {m.patient?.sex === "M" ? "Male" : m.patient?.sex === "F" ? "Female" : "Other"} • DOB: {m.patient?.dob || m.dob}
                  </p>
                  {(m.patient?.blood_group || m.blood_group) && (
                    <p className="text-xs font-semibold text-rose-500">
                      Blood Group: {m.patient?.blood_group || m.blood_group}
                    </p>
                  )}
                  {(m.patient?.phone || m.phone) && (
                    <p className="text-xs font-mono text-muted">{m.patient?.phone || m.phone}</p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteMutation.mutate(m.patient_id || m.id)}
                  loading={deleteMutation.isPending}
                >
                  <Trash2 className="size-4 text-muted hover:text-danger" />
                </Button>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
