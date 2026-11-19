"use client";

import React, { useState, useEffect } from "react";
import { SystemHeader } from "@/components/SystemHeader";
import { Sidebar } from "@/components/Sidebar";
import { ChatInterface } from "@/components/ChatInterface";
import { PropertyExplorer } from "@/components/PropertyExplorer";
import { CitationDrawer } from "@/components/CitationDrawer";
import { AboutModal } from "@/components/AboutModal";
import { useChatStream } from "@/hooks/useChatStream";
import { PropertyItem, HealthStatus } from "@/lib/types";
import { fetchHealth } from "@/lib/api";

export default function Home() {
  const {
    messages,
    isLoading,
    sourceFilter,
    setSourceFilter,
    selectedCitation,
    setSelectedCitation,
    sendMessage,
    startNewConversation,
    currentSessionId,
    sessions,
    selectSession,
    deleteSession,
  } = useChatStream();

  const [activeView, setActiveView] = useState<"chat" | "properties">("chat");
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [isAboutModalOpen, setIsAboutModalOpen] = useState<boolean>(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err) => console.warn("Backend telemetry pending:", err));

    const timer = setInterval(() => {
      fetchHealth().then(setHealth).catch(() => {});
    }, 15000);

    return () => clearInterval(timer);
  }, []);

  const handleAskAboutProperty = (property: PropertyItem) => {
    const prompt = `Tell me all available details about ${property.title} in ${property.city}, ${property.country}. What are its key specifications, starting price, developer, and luxury amenities?`;
    setActiveView("chat");
    sendMessage(prompt);
  };

  return (
    <div className="flex h-screen bg-charcoal-950 text-zinc-100 overflow-hidden font-sans selection:bg-gold-500/30 selection:text-gold-200">
      {/* Platform Sidebar */}
      <Sidebar
        currentSessionId={currentSessionId}
        sessions={sessions}
        onSelectSession={selectSession}
        onNewSession={startNewConversation}
        onDeleteSession={deleteSession}
        onOpenAbout={() => setIsAboutModalOpen(true)}
        activeView={activeView}
        setActiveView={setActiveView}
        health={health}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
        {/* Executive Header */}
        <SystemHeader
          sourceFilter={sourceFilter}
          setSourceFilter={setSourceFilter}
          health={health}
          onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          activeView={activeView}
          setActiveView={setActiveView}
          onOpenAbout={() => setIsAboutModalOpen(true)}
        />

        {/* View Router */}
        <main className="flex-1 overflow-hidden relative">
          {activeView === "chat" ? (
            <div className="h-full w-full">
              <ChatInterface
                messages={messages}
                isLoading={isLoading}
                onSendMessage={sendMessage}
                onSelectCitation={setSelectedCitation}
                sourceFilter={sourceFilter}
              />
            </div>
          ) : (
            <div className="h-full w-full">
              <PropertyExplorer
                onAskAboutProperty={handleAskAboutProperty}
                sourceFilter={sourceFilter}
                setSourceFilter={setSourceFilter}
                isFullView={true}
              />
            </div>
          )}
        </main>

        {/* Source Citation Inspector Drawer */}
        <CitationDrawer
          citation={selectedCitation}
          onClose={() => setSelectedCitation(null)}
        />

        {/* About & Data Provenance Transparency Modal */}
        <AboutModal
          isOpen={isAboutModalOpen}
          onClose={() => setIsAboutModalOpen(false)}
          health={health}
        />
      </div>
    </div>
  );
}
