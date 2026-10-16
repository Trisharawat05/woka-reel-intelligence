"use client";

import React, { useState, useEffect } from "react";
import {
  Bot,
  Plus,
  Play,
  CheckCircle2,
  AlertCircle,
  Trash2,
  Edit2,
  Clock,
  Sparkles,
  Send,
  Smartphone,
  Check,
  RefreshCw
} from "lucide-react";
import { api } from "@/lib/api";
import { Automation, AutomationLog } from "@/types";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea } from "@/components/ui/input";
import { Modal } from "@/components/ui/dialog";

export default function AutomationsPage() {
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [logs, setLogs] = useState<AutomationLog[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [keywords, setKeywords] = useState("");
  const [dmTemplate, setDmTemplate] = useState("");
  const [replyTemplate, setReplyTemplate] = useState("");
  const [matchType, setMatchType] = useState("CONTAINS_ANY");
  const [cooldown, setCooldown] = useState(60);

  // Simulator State
  const [simComment, setSimComment] = useState("Could you send the toolkit link please?");
  const [simAuthor, setSimAuthor] = useState("creative_fan");
  const [simResult, setSimResult] = useState<any | null>(null);
  const [simulating, setSimulating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [autos, logList] = await Promise.all([
        api.listAutomations(),
        api.getAutomationLogs()
      ]);
      setAutomations(autos);
      setLogs(logList);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCreateModal = () => {
    setEditingId(null);
    setName("");
    setKeywords("link, guide, free");
    setDmTemplate("Hey {{username}}! Thanks for commenting. Here is your link: https://woka.io/resources Enjoy!");
    setReplyTemplate("Sent to your DMs {{username}}! Check your messages 💌");
    setMatchType("CONTAINS_ANY");
    setCooldown(60);
    setIsModalOpen(true);
  };

  const handleSaveAutomation = async (e: React.FormEvent) => {
    e.preventDefault();
    const keywordArray = keywords.split(",").map((k) => k.trim()).filter(Boolean);
    const payload = {
      name,
      trigger_type: "COMMENT",
      target_post_type: "ALL_POSTS",
      match_type: matchType,
      trigger_keywords: keywordArray,
      dm_message_template: dmTemplate,
      reply_comment_template: replyTemplate,
      cooldown_minutes: Number(cooldown),
      is_active: true
    };

    if (editingId) {
      await api.updateAutomation(editingId, payload);
    } else {
      await api.createAutomation(payload);
    }

    setIsModalOpen(false);
    loadData();
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this automation?")) {
      await api.deleteAutomation(id);
      loadData();
    }
  };

  const handleToggleActive = async (auto: Automation) => {
    await api.updateAutomation(auto.id, { is_active: !auto.is_active });
    loadData();
  };

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    try {
      const res = await api.simulateAutomation({
        comment_text: simComment,
        comment_author: simAuthor
      });
      setSimResult(res);
      // Reload logs after simulation
      api.getAutomationLogs().then(setLogs);
    } finally {
      setSimulating(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            Instagram Comment-to-DM Automations
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Automatically reply to post comments and send private DMs containing your links, guides, or discount codes.
          </p>
        </div>

        <Button variant="gradient" onClick={handleOpenCreateModal} className="h-10">
          <Plus className="h-4 w-4 mr-2" />
          <span>New Comment Automation</span>
        </Button>
      </div>

      {/* Interactive Simulator Section */}
      <Card className="border-violet-200 bg-gradient-to-r from-violet-50/50 to-rose-50/50 shadow-sm">
        <CardHeader>
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-violet-600 flex items-center justify-center text-white">
              <Play className="h-4 w-4" />
            </div>
            <div>
              <CardTitle className="text-base">Interactive Trigger Simulator</CardTitle>
              <CardDescription className="text-xs">
                Test your keywords and preview the outbound DM without posting on real Instagram.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
            {/* Input Form */}
            <form onSubmit={handleRunSimulation} className="space-y-3">
              <Input
                label="Simulated Commenter Handle"
                value={simAuthor}
                onChange={(e) => setSimAuthor(e.target.value)}
                placeholder="creative_fan"
                required
              />
              <Input
                label="Comment Text"
                value={simComment}
                onChange={(e) => setSimComment(e.target.value)}
                placeholder="Could you send the link please?"
                required
              />
              <Button type="submit" variant="gradient" className="w-full h-10" isLoading={simulating}>
                <Send className="h-4 w-4 mr-2" />
                <span>Simulate Comment Trigger</span>
              </Button>
            </form>

            {/* Live Result Phone Preview */}
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm min-h-[160px] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                  <span className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                    <Smartphone className="h-4 w-4 text-violet-600" />
                    Instagram Direct Preview
                  </span>
                  {simResult && (
                    <Badge variant={simResult.matched ? "success" : "warning"} className="text-[10px]">
                      {simResult.status}
                    </Badge>
                  )}
                </div>

                {simResult ? (
                  <div className="space-y-3">
                    {simResult.matched ? (
                      <>
                        <div className="rounded-2xl rounded-tl-sm bg-violet-600 p-3 text-xs text-white max-w-[85%] shadow-sm">
                          {simResult.dm_message_preview}
                        </div>
                        <div className="text-[11px] text-slate-500 bg-slate-50 rounded-lg p-2 border border-slate-100">
                          <strong>Public Comment Reply:</strong> &quot;{simResult.reply_comment_preview}&quot;
                        </div>
                      </>
                    ) : (
                      <div className="text-xs text-slate-500 py-3 text-center">
                        <AlertCircle className="h-6 w-6 text-amber-500 mx-auto mb-1" />
                        <p>{simResult.explanation}</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="py-6 text-center text-xs text-slate-400">
                    Type a comment and click &quot;Simulate Comment Trigger&quot; to preview the automatic response.
                  </div>
                )}
              </div>

              {simResult?.matched && (
                <div className="mt-2 text-[10px] text-emerald-600 font-medium flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Trigger rule successfully executed and logged
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Rules List */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-slate-900">Configured Automations ({automations.length})</h3>

        {automations.length === 0 ? (
          <Card className="p-8 text-center text-slate-500">
            <Bot className="h-8 w-8 mx-auto text-slate-400 mb-2" />
            <p className="text-sm">No automations configured yet.</p>
            <Button variant="gradient" size="sm" onClick={handleOpenCreateModal} className="mt-3">
              Create Your First Rule
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {automations.map((auto) => (
              <Card key={auto.id} className="p-5 flex flex-col justify-between hover:border-violet-300">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-slate-900">{auto.name}</span>
                    <button
                      onClick={() => handleToggleActive(auto)}
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold transition-colors ${
                        auto.is_active
                          ? "bg-emerald-100 text-emerald-800 hover:bg-emerald-200"
                          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                      }`}
                    >
                      {auto.is_active ? "Active" : "Paused"}
                    </button>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="text-slate-600">
                      <strong>Trigger Keywords:</strong>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {auto.trigger_keywords.map((kw) => (
                        <span key={kw} className="bg-violet-50 text-violet-700 font-mono px-2 py-0.5 rounded text-[11px] border border-violet-100">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-lg bg-slate-50 border border-slate-100 p-3 text-xs text-slate-700">
                    <span className="font-semibold text-slate-900 block mb-1">Outbound Direct Message:</span>
                    <p className="italic">&quot;{auto.dm_message_template}&quot;</p>
                  </div>
                </div>

                <div className="flex items-center justify-between border-t border-slate-100 pt-3 mt-4 text-xs text-slate-500">
                  <span><strong>{auto.total_triggered_count}</strong> executions</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleDelete(auto.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 transition-colors"
                      title="Delete rule"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Execution Logs Table */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-slate-900">Execution History & Audit Log</h3>
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Recipient</th>
                  <th className="px-4 py-3">Inbound Comment</th>
                  <th className="px-4 py-3">Direct Message Sent</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                      No execution logs found.
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 whitespace-nowrap text-slate-400">
                        {new Date(log.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900">
                        @{log.recipient_username}
                      </td>
                      <td className="px-4 py-3 italic max-w-xs truncate text-slate-700">
                        &quot;{log.trigger_comment_text}&quot;
                      </td>
                      <td className="px-4 py-3 max-w-sm truncate text-slate-600">
                        {log.dm_text_sent}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap">
                        <Badge
                          variant={log.status === "SUCCESS" ? "success" : log.status === "SIMULATED" ? "sandbox" : "danger"}
                          className="text-[10px]"
                        >
                          {log.status}
                        </Badge>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* Create / Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingId ? "Edit Automation" : "Create New Comment-to-DM Trigger"}
        description="Set up triggers that automatically message users when they leave specific keywords."
      >
        <form onSubmit={handleSaveAutomation} className="space-y-4 text-xs">
          <Input
            label="Automation Internal Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Free 2026 Creator Toolkit Guide"
            required
          />

          <Input
            label="Trigger Keywords (comma separated)"
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            placeholder="link, guide, free, tools"
            required
          />

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
              Keyword Matching Logic
            </label>
            <select
              value={matchType}
              onChange={(e) => setMatchType(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <option value="CONTAINS_ANY">Contains Any Keyword (Recommended)</option>
              <option value="EXACT_MATCH">Exact Match Only</option>
              <option value="ANY_COMMENT">Trigger on Any Comment</option>
            </select>
          </div>

          <Textarea
            label="Direct Message Template"
            value={dmTemplate}
            onChange={(e) => setDmTemplate(e.target.value)}
            placeholder="Hey {{username}}! Thanks for commenting. Here is the link..."
            required
          />
          <span className="text-[11px] text-slate-600 block -mt-2">
            Use variables like <code>&#123;&#123;username&#125;&#125;</code> to personalize the outbound DM.
          </span>

          <Input
            label="Optional Public Reply to Comment"
            value={replyTemplate}
            onChange={(e) => setReplyTemplate(e.target.value)}
            placeholder="Sent you a DM {{username}}! 💌"
          />

          <Input
            label="Anti-Spam Cooldown (Minutes per User)"
            type="number"
            value={cooldown}
            onChange={(e) => setCooldown(Number(e.target.value))}
            min={1}
            required
          />

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
            <Button type="button" variant="secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="gradient">
              Save Automation &rarr;
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
