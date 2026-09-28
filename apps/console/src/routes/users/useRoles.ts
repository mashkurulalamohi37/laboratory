import { unwrap } from "@nirnoy/api-client";
import { useAuth } from "@nirnoy/app-core";
import { useQuery } from "@tanstack/react-query";

export function useRoles() {
  const { api } = useAuth();
  return useQuery({
    queryKey: ["admin-roles"],
    queryFn: () => unwrap(api.GET("/api/v1/admin/roles")),
    staleTime: 5 * 60_000,
  });
}
