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
import { Building, Home, MapPin, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router";

interface AddAddressFormData {
  label: "HOME" | "WORK" | "OTHER";
  house: string;
  road?: string;
  block?: string;
  landmark?: string;
}

export default function AddressesPage() {
  const { api } = useAuth();
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);

  const {
    data: addresses,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["patient-addresses"],
    queryFn: () => unwrap(api.GET("/api/v1/addresses")),
  });

  const form = useForm<AddAddressFormData>({
    defaultValues: {
      label: "HOME",
      house: "",
      road: "",
      block: "",
      landmark: "",
    },
  });

  const addMutation = useMutation({
    mutationFn: (data: AddAddressFormData) =>
      unwrap(
        api.POST("/api/v1/addresses", {
          body: {
            label: data.label,
            house: data.house,
            road: data.road || undefined,
            block: data.block || undefined,
            landmark: data.landmark || undefined,
            is_default: false,
          },
        }),
      ),
    onSuccess: () => {
      toast.success("Address added successfully");
      setShowAddForm(false);
      form.reset();
      void queryClient.invalidateQueries({ queryKey: ["patient-addresses"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to save address");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (addressId: string) =>
      unwrap(
        api.DELETE("/api/v1/addresses/{address_id}", {
          params: { path: { address_id: addressId } },
        }),
      ),
    onSuccess: () => {
      toast.success("Address removed");
      void queryClient.invalidateQueries({ queryKey: ["patient-addresses"] });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to remove address");
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
            <span>Saved Addresses</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">Saved Addresses</h1>
          <p className="mt-1 text-sm text-muted">
            Manage your home and office locations for fast doorstep sample collection.
          </p>
        </div>
        <Button
          onClick={() => setShowAddForm(!showAddForm)}
          variant={showAddForm ? "secondary" : "primary"}
        >
          <Plus className="size-4" />
          {showAddForm ? "Close Form" : "Add New Address"}
        </Button>
      </div>

      {showAddForm && (
        <Card className="mb-8 border-brand/30 shadow-md">
          <CardHeader
            title="Add New Collection Address"
            description="Provide exact house and road information for our phlebotomist."
          />
          <CardBody>
            <form
              onSubmit={form.handleSubmit((d) => addMutation.mutate(d))}
              className="grid gap-4 sm:grid-cols-2"
            >
              <Field label="Address Label" required>
                <Select {...form.register("label", { required: true })}>
                  <option value="HOME">Home</option>
                  <option value="WORK">Work / Office</option>
                  <option value="OTHER">Other</option>
                </Select>
              </Field>

              <Field label="House / Flat / Level No." required>
                <Input placeholder="e.g. Flat 4B, House 12" {...form.register("house", { required: true })} />
              </Field>

              <Field label="Street / Road Address" className="sm:col-span-2">
                <Input
                  placeholder="e.g. Road 27, Dhanmondi"
                  {...form.register("road")}
                />
              </Field>

              <Field label="Block / Sector">
                <Input placeholder="e.g. Block C / Sector 7" {...form.register("block")} />
              </Field>

              <Field label="Nearby Landmark">
                <Input placeholder="e.g. Near Star Kabab" {...form.register("landmark")} />
              </Field>

              <div className="flex gap-2 sm:col-span-2">
                <Button type="submit" loading={addMutation.isPending}>
                  Save Address
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
        <LoadingRows rows={3} label="Loading saved addresses..." />
      ) : isError ? (
        <Alert tone="danger">Failed to load addresses.</Alert>
      ) : !addresses || addresses.length === 0 ? (
        <Card>
          <CardBody className="py-12 text-center">
            <MapPin className="mx-auto mb-3 size-12 text-muted" />
            <h3 className="text-lg font-bold text-foreground">No saved addresses</h3>
            <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
              Add your home or office address to enable quick 1-click home sample collection bookings.
            </p>
            <Button className="mt-4" onClick={() => setShowAddForm(true)}>
              <Plus className="size-4" />
              Add First Address
            </Button>
          </CardBody>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {addresses.map((a: any) => (
            <Card interactive key={a.id} className="border border-border">
              <CardBody className="flex items-start justify-between p-5">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1.5 font-bold text-foreground">
                      {a.label === "OFFICE" ? (
                        <Building className="size-4 text-brand" />
                      ) : (
                        <Home className="size-4 text-brand" />
                      )}
                      {a.label}
                    </span>
                    {a.is_default && <Badge tone="brand">Default</Badge>}
                  </div>
                  <p className="text-sm font-medium text-foreground">{a.house}</p>
                  {a.road && <p className="text-sm text-muted">{a.road}</p>}
                  {a.landmark && (
                    <p className="text-xs text-muted">
                      Landmark: {a.landmark}
                    </p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteMutation.mutate(a.id)}
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
