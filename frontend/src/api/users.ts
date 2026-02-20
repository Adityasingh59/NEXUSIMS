/**
 * NEXUS IMS — Users API client (Block 4)
 */
import { apiClient as axios } from "../lib/api";

export interface UserResponse {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  warehouse_scope: string[] | null;
  is_active: boolean;
}

export interface InviteRequest {
  email: string;
  role: string;
  warehouse_scope?: string[] | null;
}

export interface AcceptInvitationRequest {
  token: string;
  password: string;
  full_name?: string;
}

export interface UpdateRoleRequest {
  role: string;
  warehouse_scope?: string[] | null;
}

export async function inviteUser(
  data: InviteRequest
): Promise<{ message: string; dev_token: string }> {
  const res = await axios.post("/api/v1/users/invite", data);
  return res.data.data;
}

export async function acceptInvitation(
  data: AcceptInvitationRequest
): Promise<UserResponse> {
  const res = await axios.post("/api/v1/users/accept-invitation", data);
  return res.data.data;
}

export async function listUsers(
  includeInactive = false
): Promise<UserResponse[]> {
  const res = await axios.get("/api/v1/users", {
    params: { include_inactive: includeInactive },
  });
  return res.data.data;
}

export async function updateUserRole(
  userId: string,
  data: UpdateRoleRequest
): Promise<UserResponse> {
  const res = await axios.put(`/api/v1/users/${userId}/role`, data);
  return res.data.data;
}

export async function deactivateUser(userId: string): Promise<void> {
  await axios.delete(`/api/v1/users/${userId}`);
}
