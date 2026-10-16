import {
  User, Workspace, InstagramAccount, Automation, AutomationLog,
  AnalyticsResponse, CreatorProfile, BrandCampaign, CampaignApplication,
  Invoice, Subscription, NotificationItem
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private getToken(): string | null {
    if (typeof window !== "undefined") {
      return localStorage.getItem("woka_token");
    }
    return null;
  }

  setToken(token: string) {
    if (typeof window !== "undefined") {
      localStorage.setItem("woka_token", token);
    }
  }

  clearToken() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("woka_token");
      localStorage.removeItem("woka_user");
      localStorage.removeItem("woka_workspace");
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const message = errorData.detail || `Request failed with status ${response.status}`;
      throw new Error(message);
    }

    return response.json();
  }

  // Auth
  async register(data: any): Promise<{ access_token: string; user: User; workspace: Workspace }> {
    const res = await this.request<{ access_token: string; user: User; workspace: Workspace }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    return res;
  }

  async login(data: any): Promise<{ access_token: string; user: User; workspace: Workspace }> {
    const res = await this.request<{ access_token: string; user: User; workspace: Workspace }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
    this.setToken(res.access_token);
    return res;
  }

  async getMe(): Promise<{ access_token: string; user: User; workspace: Workspace }> {
    return this.request("/auth/me");
  }

  // Instagram
  async getInstagramAccount(): Promise<InstagramAccount | null> {
    return this.request("/instagram/account");
  }

  async getOAuthUrl(): Promise<{ oauth_url: string; state: string }> {
    return this.request("/instagram/oauth-url");
  }

  async toggleSandbox(enabled: boolean, username?: string, followers_count?: number): Promise<InstagramAccount> {
    return this.request("/instagram/sandbox/toggle", {
      method: "POST",
      body: JSON.stringify({ enabled, username, followers_count }),
    });
  }

  // Automations
  async listAutomations(): Promise<Automation[]> {
    return this.request("/automations");
  }

  async createAutomation(data: any): Promise<Automation> {
    return this.request("/automations", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateAutomation(id: string, data: any): Promise<Automation> {
    return this.request(`/automations/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteAutomation(id: string): Promise<void> {
    return this.request(`/automations/${id}`, {
      method: "DELETE",
    });
  }

  async simulateAutomation(data: { comment_text: string; comment_author: string; post_id?: string; automation_id?: string }) {
    return this.request<any>("/automations/simulate", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getAutomationLogs(): Promise<AutomationLog[]> {
    return this.request("/automations/logs");
  }

  // Analytics
  async getAnalytics(): Promise<AnalyticsResponse> {
    return this.request("/analytics");
  }

  // AI Content Studio
  async generateCaption(data: any): Promise<any> {
    return this.request("/ai-studio/caption", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async generateHooks(data: any): Promise<{ hooks: string[] }> {
    return this.request("/ai-studio/hooks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async generateHashtags(data: any): Promise<any> {
    return this.request("/ai-studio/hashtags", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Media Kit
  async getMyProfile(): Promise<CreatorProfile> {
    return this.request("/media-kit/my-profile");
  }

  async updateProfile(data: any): Promise<CreatorProfile> {
    return this.request("/media-kit/my-profile", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async getPublicProfile(slug: string): Promise<CreatorProfile> {
    return this.request(`/media-kit/public/${slug}`);
  }

  async submitInquiry(slug: string, data: any): Promise<any> {
    return this.request(`/media-kit/public/${slug}/inquire`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Campaigns
  async listCampaigns(niche?: string): Promise<BrandCampaign[]> {
    const query = niche ? `?niche=${encodeURIComponent(niche)}` : "";
    return this.request(`/campaigns${query}`);
  }

  async createCampaign(data: any): Promise<BrandCampaign> {
    return this.request("/campaigns", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getCampaign(id: string): Promise<BrandCampaign> {
    return this.request(`/campaigns/${id}`);
  }

  async applyToCampaign(id: string, data: any): Promise<CampaignApplication> {
    return this.request(`/campaigns/${id}/apply`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getMyApplications(): Promise<CampaignApplication[]> {
    return this.request("/campaigns/my-applications");
  }

  async getCampaignApplications(id: string): Promise<CampaignApplication[]> {
    return this.request(`/campaigns/${id}/applications`);
  }

  async updateApplicationStatus(id: string, status: string): Promise<CampaignApplication> {
    return this.request(`/campaigns/applications/${id}/status?new_status=${status}`, {
      method: "PUT",
    });
  }

  async submitDeliverable(applicationId: string, data: any) {
    return this.request(`/campaigns/applications/${applicationId}/deliverables`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Invoices & Rate Calculator
  async listInvoices(): Promise<Invoice[]> {
    return this.request("/invoices");
  }

  async createInvoice(data: any): Promise<Invoice> {
    return this.request("/invoices", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateInvoiceStatus(id: string, status: string): Promise<Invoice> {
    return this.request(`/invoices/${id}/status?status=${status}`, {
      method: "PUT",
    });
  }

  async calculateRate(data: any) {
    return this.request<any>("/invoices/calculate-rate", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Subscriptions
  async getSubscription(): Promise<Subscription> {
    return this.request("/subscriptions/current");
  }

  async upgradeSubscription(target_tier: string): Promise<Subscription> {
    return this.request("/subscriptions/upgrade", {
      method: "POST",
      body: JSON.stringify({ target_tier }),
    });
  }

  // Notifications
  async listNotifications(): Promise<NotificationItem[]> {
    return this.request("/notifications");
  }

  async markNotificationRead(id: string): Promise<void> {
    return this.request(`/notifications/${id}/read`, {
      method: "PUT",
    });
  }

  async markAllNotificationsRead(): Promise<void> {
    return this.request("/notifications/read-all", {
      method: "PUT",
    });
  }

  // Admin
  async getAdminStats(): Promise<any> {
    return this.request("/admin/stats");
  }

  async listAdminUsers(): Promise<User[]> {
    return this.request("/admin/users");
  }
}

export const api = new ApiClient();
