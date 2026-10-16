"use client";

import React, { useState, useEffect } from "react";
import {
  Receipt,
  Plus,
  Calculator,
  CheckCircle2,
  Clock,
  Printer,
  DollarSign,
  Download,
  AlertCircle,
  TrendingUp,
  FileText
} from "lucide-react";
import { api } from "@/lib/api";
import { Invoice, InvoiceLineItem } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/dialog";
import { formatCurrency } from "@/lib/utils";

export default function InvoicesAndRatesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  // Rate Calculator State
  const [calcFollowers, setCalcFollowers] = useState(48500);
  const [calcReach, setCalcReach] = useState(19500);
  const [calcER, setCalcER] = useState(4.25);
  const [calcType, setCalcType] = useState("REEL");
  const [calcResult, setCalcResult] = useState<any | null>(null);
  const [calculating, setCalculating] = useState(false);

  // Create Invoice Modal State
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [clientName, setClientName] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [dueDate, setDueDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 15);
    return d.toISOString().split("T")[0];
  });
  const [notes, setNotes] = useState("Payment due within 15 days via wire transfer.");
  const [lineItems, setLineItems] = useState<InvoiceLineItem[]>([
    { description: "1x Dedicated Instagram 60s Reel", quantity: 1, unit_price: 450, total: 450 }
  ]);
  const [creatingInvoice, setCreatingInvoice] = useState(false);

  useEffect(() => {
    loadInvoices();
    handleRunCalculator();
  }, []);

  const loadInvoices = async () => {
    try {
      const list = await api.listInvoices();
      setInvoices(list);
    } finally {
      setLoading(false);
    }
  };

  const handleRunCalculator = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setCalculating(true);
    try {
      const res = await api.calculateRate({
        followers: Number(calcFollowers),
        avg_reach: Number(calcReach),
        engagement_rate: Number(calcER),
        deliverable_type: calcType,
      });
      setCalcResult(res);
    } finally {
      setCalculating(false);
    }
  };

  const handleAddLineItem = () => {
    setLineItems((prev) => [
      ...prev,
      { description: "2x Instagram Stories (Frames)", quantity: 1, unit_price: 100, total: 100 }
    ]);
  };

  const handleUpdateLineItem = (index: number, field: string, value: any) => {
    setLineItems((prev) => {
      const updated = [...prev];
      const item = { ...updated[index], [field]: value };
      if (field === "quantity" || field === "unit_price") {
        item.total = Number(item.quantity) * Number(item.unit_price);
      }
      updated[index] = item;
      return updated;
    });
  };

  const handleRemoveLineItem = (index: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const totalInvoiceSum = lineItems.reduce((acc, item) => acc + (item.total || 0), 0);

  const handleSaveInvoice = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingInvoice(true);
    try {
      await api.createInvoice({
        client_name: clientName,
        client_email: clientEmail,
        currency: "USD",
        due_date: dueDate,
        line_items: lineItems,
        notes,
      });
      setCreateModalOpen(false);
      loadInvoices();
    } finally {
      setCreatingInvoice(false);
    }
  };

  const handleUpdateStatus = async (invoiceId: string, status: string) => {
    await api.updateInvoiceStatus(invoiceId, status);
    loadInvoices();
  };

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Invoicing & Dynamic Rate Calculator
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Price deliverables with market CPM benchmarks and bill brand sponsors with 1-click status tracking.
          </p>
        </div>

        <Button variant="gradient" onClick={() => setCreateModalOpen(true)} className="h-10">
          <Plus className="h-4 w-4 mr-1.5" />
          <span>Create New Invoice</span>
        </Button>
      </div>

      {/* Rate Calculator Card */}
      <Card className="border-violet-200 bg-gradient-to-r from-violet-50/50 to-rose-50/50 shadow-sm">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-violet-600 flex items-center justify-center text-white">
              <Calculator className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base">Benchmark Creator Pricing Calculator</CardTitle>
              <CardDescription className="text-xs">
                Generates defensible sponsorship rates based on verified reach and audience engagement multipliers.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
            {/* Input Form */}
            <form onSubmit={handleRunCalculator} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Instagram Followers"
                  type="number"
                  value={calcFollowers}
                  onChange={(e) => setCalcFollowers(Number(e.target.value))}
                  required
                />
                <Input
                  label="Average Reel / Post Reach"
                  type="number"
                  value={calcReach}
                  onChange={(e) => setCalcReach(Number(e.target.value))}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Engagement Rate (%)"
                  type="number"
                  step="0.1"
                  value={calcER}
                  onChange={(e) => setCalcER(Number(e.target.value))}
                  required
                />

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                    Deliverable Format
                  </label>
                  <select
                    value={calcType}
                    onChange={(e) => setCalcType(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                  >
                    <option value="REEL">Dedicated 60s Reel (1.0x)</option>
                    <option value="STORY_SET">3x Story Frames (0.45x)</option>
                    <option value="POST">Feed Photo / Carousel (0.7x)</option>
                    <option value="BUNDLE">Reel + Story + Link Bundle (1.65x)</option>
                  </select>
                </div>
              </div>

              <Button type="submit" variant="gradient" className="w-full h-10" isLoading={calculating}>
                <span>Recalculate Benchmark Pricing</span>
              </Button>
            </form>

            {/* Result Box */}
            {calcResult && (
              <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm flex flex-col justify-between">
                <div>
                  <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    Recommended Deliverable Quote
                  </span>
                  <div className="text-4xl font-black text-slate-900 mt-2">
                    {formatCurrency(calcResult.recommended_rate)}
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-xs text-slate-500 font-medium">
                    <span>Floor: <strong>{formatCurrency(calcResult.min_rate)}</strong></span>
                    <span>•</span>
                    <span>High Cap: <strong>{formatCurrency(calcResult.max_rate)}</strong></span>
                  </div>
                </div>

                <div className="mt-5 rounded-lg bg-slate-50 border border-slate-100 p-3 text-xs text-slate-600 leading-relaxed">
                  <span className="font-semibold text-slate-800 block mb-1">Pricing Rationale:</span>
                  <p>{calcResult.reasoning}</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Invoices List */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-slate-900">Invoices & Payment Tracking ({invoices.length})</h3>

        {invoices.length === 0 ? (
          <Card className="p-12 text-center text-slate-500">
            <Receipt className="h-8 w-8 mx-auto text-slate-400 mb-2" />
            <p className="text-sm">No invoices created yet.</p>
            <Button variant="gradient" size="sm" onClick={() => setCreateModalOpen(true)} className="mt-3">
              Generate Your First Brand Invoice
            </Button>
          </Card>
        ) : (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Invoice #</th>
                    <th className="px-4 py-3">Client</th>
                    <th className="px-4 py-3">Amount</th>
                    <th className="px-4 py-3">Due Date</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 font-mono font-semibold text-slate-900">
                        {inv.invoice_number}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-semibold text-slate-900 block">{inv.client_name}</span>
                        <span className="text-[10px] text-slate-400">{inv.client_email}</span>
                      </td>
                      <td className="px-4 py-3 font-bold text-slate-900 text-sm">
                        {formatCurrency(inv.total_amount, inv.currency)}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {inv.due_date}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant={inv.status === "PAID" ? "success" : inv.status === "SENT" ? "default" : "secondary"}
                          className="text-[10px]"
                        >
                          {inv.status}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right space-x-2">
                        {inv.status !== "PAID" && (
                          <Button
                            variant="secondary"
                            size="sm"
                            className="text-[11px] h-7 px-2"
                            onClick={() => handleUpdateStatus(inv.id, "PAID")}
                          >
                            Mark Paid
                          </Button>
                        )}
                        {inv.status === "DRAFT" && (
                          <Button
                            variant="secondary"
                            size="sm"
                            className="text-[11px] h-7 px-2"
                            onClick={() => handleUpdateStatus(inv.id, "SENT")}
                          >
                            Mark Sent
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>

      {/* Modal: Create Invoice */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Generate Brand Sponsor Invoice"
        description="Create an itemized invoice for deliverables."
      >
        <form onSubmit={handleSaveInvoice} className="space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Client / Brand Name"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="e.g. Lumin Audio Tech"
              required
            />
            <Input
              label="Client Billing Email"
              type="email"
              value={clientEmail}
              onChange={(e) => setClientEmail(e.target.value)}
              placeholder="billing@luminaudio.com"
              required
            />
          </div>

          <Input
            label="Payment Due Date"
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            required
          />

          {/* Line Items */}
          <div className="space-y-3 border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-800">Deliverable Line Items</span>
              <button
                type="button"
                onClick={handleAddLineItem}
                className="text-xs font-semibold text-violet-600 hover:underline"
              >
                + Add Item
              </button>
            </div>

            {lineItems.map((item, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2 items-center bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                <div className="col-span-6">
                  <input
                    type="text"
                    value={item.description}
                    onChange={(e) => handleUpdateLineItem(idx, "description", e.target.value)}
                    placeholder="Deliverable description"
                    className="w-full text-xs rounded border border-slate-200 px-2 py-1.5"
                    required
                  />
                </div>
                <div className="col-span-2">
                  <input
                    type="number"
                    value={item.quantity}
                    onChange={(e) => handleUpdateLineItem(idx, "quantity", Number(e.target.value))}
                    min={1}
                    className="w-full text-xs rounded border border-slate-200 px-2 py-1.5"
                    required
                  />
                </div>
                <div className="col-span-3">
                  <input
                    type="number"
                    value={item.unit_price}
                    onChange={(e) => handleUpdateLineItem(idx, "unit_price", Number(e.target.value))}
                    min={0}
                    className="w-full text-xs rounded border border-slate-200 px-2 py-1.5"
                    required
                  />
                </div>
                <div className="col-span-1 text-center">
                  <button
                    type="button"
                    onClick={() => handleRemoveLineItem(idx)}
                    className="text-rose-500 hover:text-rose-700 text-sm font-bold"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}

            <div className="flex justify-between items-center text-sm font-bold text-slate-900 pt-2 border-t border-slate-100">
              <span>Total Payable:</span>
              <span>{formatCurrency(totalInvoiceSum)}</span>
            </div>
          </div>

          <Textarea
            label="Payment Instructions / Notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
          />

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <Button type="button" variant="secondary" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="gradient" isLoading={creatingInvoice}>
              Generate Invoice &rarr;
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
