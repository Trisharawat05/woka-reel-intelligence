"use client";

import React, { useState } from "react";
import {
  Sparkles,
  Copy,
  Check,
  Flame,
  Hash,
  Send,
  RefreshCw,
  BookOpen,
  Zap,
  Bookmark
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input, Textarea } from "@/components/ui/input";

export default function AIStudioPage() {
  const [activeTab, setActiveTab] = useState<"caption" | "hooks" | "hashtags">("caption");

  // Caption Generator State
  const [captionTopic, setCaptionTopic] = useState("5 secret tools every creator needs in 2026 to automate their growth");
  const [tone, setTone] = useState("Engaging");
  const [cta, setCta] = useState("Comment for Link");
  const [includeEmojis, setIncludeEmojis] = useState(true);
  const [generatedCaption, setGeneratedCaption] = useState<any | null>(null);
  const [loadingCaption, setLoadingCaption] = useState(false);
  const [copiedCaption, setCopiedCaption] = useState(false);

  // Hook Generator State
  const [hookTopic, setHookTopic] = useState("building a $10k creator business with 30k followers");
  const [hookStyle, setHookStyle] = useState("Curiosity Gap");
  const [hooks, setHooks] = useState<string[]>([]);
  const [loadingHooks, setLoadingHooks] = useState(false);
  const [copiedHookIdx, setCopiedHookIdx] = useState<number | null>(null);

  // Hashtag Generator State
  const [hashtagNiche, setHashtagNiche] = useState("tech creator");
  const [hashtags, setHashtags] = useState<any | null>(null);
  const [loadingHashtags, setLoadingHashtags] = useState(false);
  const [copiedTags, setCopiedTags] = useState(false);

  const handleGenerateCaption = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingCaption(true);
    try {
      const res = await api.generateCaption({
        topic: captionTopic,
        tone,
        target_cta: cta,
        include_emojis: includeEmojis,
      });
      setGeneratedCaption(res);
    } finally {
      setLoadingCaption(false);
    }
  };

  const handleGenerateHooks = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingHooks(true);
    try {
      const res = await api.generateHooks({
        topic: hookTopic,
        style: hookStyle,
      });
      setHooks(res.hooks);
    } finally {
      setLoadingHooks(false);
    }
  };

  const handleGenerateHashtags = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingHashtags(true);
    try {
      const res = await api.generateHashtags({ niche: hashtagNiche });
      setHashtags(res);
    } finally {
      setLoadingHashtags(false);
    }
  };

  const copyText = (text: string, callback: () => void) => {
    navigator.clipboard.writeText(text);
    callback();
  };

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
          AI Creator Content Studio
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Craft high-retention opening hooks, structured post captions with comment CTAs, and optimized hashtag sets.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setActiveTab("caption")}
          className={`flex items-center gap-2 py-3 px-5 border-b-2 font-semibold text-sm transition-colors ${
            activeTab === "caption"
              ? "border-violet-600 text-violet-700 bg-violet-50/40"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Sparkles className="h-4 w-4" />
          <span>Caption Generator</span>
        </button>

        <button
          onClick={() => setActiveTab("hooks")}
          className={`flex items-center gap-2 py-3 px-5 border-b-2 font-semibold text-sm transition-colors ${
            activeTab === "hooks"
              ? "border-violet-600 text-violet-700 bg-violet-50/40"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Flame className="h-4 w-4 text-rose-500" />
          <span>Viral Reels Hooks</span>
        </button>

        <button
          onClick={() => setActiveTab("hashtags")}
          className={`flex items-center gap-2 py-3 px-5 border-b-2 font-semibold text-sm transition-colors ${
            activeTab === "hashtags"
              ? "border-violet-600 text-violet-700 bg-violet-50/40"
              : "border-transparent text-slate-500 hover:text-slate-900"
          }`}
        >
          <Hash className="h-4 w-4" />
          <span>Smart Hashtags</span>
        </button>
      </div>

      {/* Tab 1: Caption Generator */}
      {activeTab === "caption" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Prompt Your Content</CardTitle>
              <CardDescription className="text-xs">
                Describe the core idea and customize the tone and comment-to-DM trigger.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleGenerateCaption} className="space-y-4 text-xs">
                <Textarea
                  label="What is your post or Reel about?"
                  value={captionTopic}
                  onChange={(e) => setCaptionTopic(e.target.value)}
                  placeholder="e.g. 5 tools every creator needs in 2026..."
                  required
                />

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                      Tone of Voice
                    </label>
                    <select
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                    >
                      <option value="Engaging">Engaging & Relatable</option>
                      <option value="Witty">Witty & Direct</option>
                      <option value="Storytelling">Storytelling & Vulnerable</option>
                      <option value="Urgent">Urgent & Fast-Paced</option>
                      <option value="Professional">Professional Authority</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                      Target Call To Action
                    </label>
                    <select
                      value={cta}
                      onChange={(e) => setCta(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                    >
                      <option value="Comment for Link">Comment Keyword for DM Link</option>
                      <option value="Save for Later">Save for Later</option>
                      <option value="Share">Share with a Friend</option>
                      <option value="Visit Bio">Visit Link in Bio</option>
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="checkbox"
                    id="emojis"
                    checked={includeEmojis}
                    onChange={(e) => setIncludeEmojis(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500"
                  />
                  <label htmlFor="emojis" className="text-xs text-slate-700 font-medium">
                    Include engaging emojis and line breaks
                  </label>
                </div>

                <Button type="submit" variant="gradient" className="w-full h-10 mt-2" isLoading={loadingCaption}>
                  <Sparkles className="h-4 w-4 mr-2" />
                  <span>Generate Caption & Strategy</span>
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Generated Result Preview */}
          <Card className="min-h-[380px] flex flex-col justify-between">
            <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-slate-100">
              <CardTitle className="text-base">Generated Copy</CardTitle>
              {generatedCaption && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() =>
                    copyText(generatedCaption.caption, () => {
                      setCopiedCaption(true);
                      setTimeout(() => setCopiedCaption(false), 2000);
                    })
                  }
                  className="h-8 text-xs"
                >
                  {copiedCaption ? <Check className="h-3.5 w-3.5 mr-1 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                  <span>{copiedCaption ? "Copied!" : "Copy Caption"}</span>
                </Button>
              )}
            </CardHeader>
            <CardContent className="pt-4 flex-1">
              {generatedCaption ? (
                <div className="space-y-4 text-xs">
                  <div className="rounded-xl bg-slate-50 border border-slate-100 p-4 font-sans text-slate-800 whitespace-pre-line leading-relaxed">
                    {generatedCaption.caption}
                  </div>

                  <div className="space-y-1.5">
                    <span className="font-semibold text-slate-700 block">Alternative Opening Hooks:</span>
                    <ul className="list-disc list-inside text-slate-600 space-y-1">
                      {generatedCaption.suggested_hooks.map((h: string, idx: number) => (
                        <li key={idx} className="italic">&quot;{h}&quot;</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="py-20 text-center text-xs text-slate-400">
                  <Sparkles className="h-8 w-8 mx-auto text-violet-300 mb-2" />
                  <p>Click &quot;Generate Caption&quot; to produce tailored copy with hooks and keywords.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab 2: Viral Hooks */}
      {activeTab === "hooks" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Reels Hook Frameworks</CardTitle>
              <CardDescription className="text-xs">
                First 3 seconds are make-or-break. Generate retention-engineered hooks.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleGenerateHooks} className="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end text-xs">
                <div className="sm:col-span-2">
                  <Input
                    label="Reel Concept / Topic"
                    value={hookTopic}
                    onChange={(e) => setHookTopic(e.target.value)}
                    placeholder="e.g. monetizing Instagram with 20k followers"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
                    Framework
                  </label>
                  <select
                    value={hookStyle}
                    onChange={(e) => setHookStyle(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800"
                  >
                    <option value="Curiosity Gap">Curiosity Gap</option>
                    <option value="Contrarian">Contrarian Opinion</option>
                    <option value="Step-by-Step">Step-by-Step Blueprint</option>
                    <option value="Story Hook">Story & Vulnerability</option>
                    <option value="Warning">Warning & Mistake</option>
                  </select>
                </div>
                <div className="sm:col-span-3">
                  <Button type="submit" variant="gradient" className="w-full h-10" isLoading={loadingHooks}>
                    <Flame className="h-4 w-4 mr-2" />
                    <span>Generate Viral Hooks</span>
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {hooks.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-900">Generated Opening Hooks ({hooks.length})</h3>
              <div className="grid grid-cols-1 gap-3">
                {hooks.map((hook, idx) => (
                  <Card key={idx} className="p-4 flex items-center justify-between hover:border-violet-300">
                    <span className="text-sm font-medium text-slate-800 italic">
                      &quot;{hook}&quot;
                    </span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        copyText(hook, () => {
                          setCopiedHookIdx(idx);
                          setTimeout(() => setCopiedHookIdx(null), 2000);
                        })
                      }
                      className="ml-4 flex-shrink-0 text-xs"
                    >
                      {copiedHookIdx === idx ? <Check className="h-3.5 w-3.5 text-emerald-600 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                      <span>{copiedHookIdx === idx ? "Copied" : "Copy"}</span>
                    </Button>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Smart Hashtags */}
      {activeTab === "hashtags" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Smart Niche Hashtag Finder</CardTitle>
              <CardDescription className="text-xs">
                Generates reach-tiered tags (High reach, mid-tier, and hyper-niche) to optimize explore distribution.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleGenerateHashtags} className="flex flex-col sm:flex-row gap-3 items-end text-xs">
                <div className="flex-1 w-full">
                  <Input
                    label="Your Content Niche"
                    value={hashtagNiche}
                    onChange={(e) => setHashtagNiche(e.target.value)}
                    placeholder="e.g. fitness, minimalist travel, productivity"
                    required
                  />
                </div>
                <Button type="submit" variant="gradient" className="h-10 px-6 w-full sm:w-auto" isLoading={loadingHashtags}>
                  <Hash className="h-4 w-4 mr-2" />
                  <span>Find Hashtags</span>
                </Button>
              </form>
            </CardContent>
          </Card>

          {hashtags && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card>
                <CardHeader className="pb-3">
                  <Badge variant="default" className="w-fit mb-1">Broad Exposure</Badge>
                  <CardTitle className="text-sm">High Reach Tier</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5 text-xs font-mono text-violet-700">
                  {hashtags.high_reach.map((tag: string) => (
                    <div key={tag}>{tag}</div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <Badge variant="secondary" className="w-fit mb-1">Targeted Search</Badge>
                  <CardTitle className="text-sm">Mid-Tier Community</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5 text-xs font-mono text-slate-700">
                  {hashtags.mid_tier.map((tag: string) => (
                    <div key={tag}>{tag}</div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <Badge variant="success" className="w-fit mb-1">High Conversion</Badge>
                  <CardTitle className="text-sm">Hyper-Niche</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1.5 text-xs font-mono text-emerald-700">
                  {hashtags.niche_specific.map((tag: string) => (
                    <div key={tag}>{tag}</div>
                  ))}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
