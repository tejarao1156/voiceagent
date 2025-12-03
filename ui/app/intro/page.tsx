'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import {
  Sparkles,
  Zap,
  Brain,
  MessageSquare,
  Phone,
  BarChart3,
  ArrowRight,
  Globe,
  Users,
  Shield,
  Clock
} from 'lucide-react'

export default function IntroPage() {
  const router = useRouter()

  const features = [
    {
      icon: Phone,
      title: 'AI Voice Agents',
      description: 'Create intelligent voice agents that handle calls 24/7 with natural conversations',
      gradient: 'from-blue-500 to-cyan-500'
    },
    {
      icon: MessageSquare,
      title: 'Smart Messaging',
      description: 'Automated SMS responses powered by advanced AI for instant customer engagement',
      gradient: 'from-violet-500 to-fuchsia-500'
    },
    {
      icon: BarChart3,
      title: 'Real-time Analytics',
      description: 'Track call performance, conversation insights, and agent efficiency in real-time',
      gradient: 'from-emerald-500 to-teal-500'
    },
    {
      icon: Brain,
      title: 'Adaptive AI',
      description: 'Continuously learning AI that improves with every interaction and conversation',
      gradient: 'from-orange-500 to-red-500'
    }
  ]

  const stats = [
    { label: 'Active Users', value: '10K+', icon: Users },
    { label: 'Calls Handled', value: '1M+', icon: Phone },
    { label: 'Response Time', value: '<2s', icon: Clock },
    { label: 'Uptime', value: '99.9%', icon: Shield }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 overflow-hidden">
      {/* Animated Background Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-400/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-400/20 rounded-full blur-3xl animate-pulse delay-1000" />
        <div className="absolute top-1/2 left-1/2 w-96 h-96 bg-cyan-400/20 rounded-full blur-3xl animate-pulse delay-500" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 container mx-auto px-6 py-6">
        <div className="flex items-center justify-between">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center space-x-2"
          >
            <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center shadow-lg">
              <Zap className="h-6 w-6 text-white" />
            </div>
            <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              VoiceAgent
            </span>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center space-x-4"
          >
            <button
              onClick={() => router.push('/auth/login')}
              className="px-6 py-2.5 text-slate-700 font-semibold hover:text-blue-600 transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={() => router.push('/auth/signup')}
              className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold shadow-lg shadow-blue-500/30 hover:shadow-xl hover:shadow-blue-500/40 transition-all hover:scale-105"
            >
              Get Started
            </button>
          </motion.div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative z-10 container mx-auto px-6 py-20">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center space-x-2 bg-white/60 backdrop-blur-xl rounded-full px-4 py-2 mb-6 border border-white shadow-lg">
              <Sparkles className="h-4 w-4 text-purple-600" />
              <span className="text-sm font-semibold text-slate-700">Powered by Advanced AI</span>
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-6xl md:text-7xl font-black mb-6 leading-tight"
          >
            <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 bg-clip-text text-transparent">
              Transform Customer
            </span>
            <br />
            <span className="text-slate-800">
              Interactions with AI
            </span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-xl text-slate-600 mb-10 max-w-3xl mx-auto leading-relaxed"
          >
            Build intelligent voice and messaging agents that understand context, handle conversations naturally, 
            and scale effortlessly. Experience the future of customer engagement.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex items-center justify-center space-x-4"
          >
            <button
              onClick={() => router.push('/auth/signup')}
              className="group px-8 py-4 rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 text-white font-bold text-lg shadow-2xl shadow-blue-500/40 hover:shadow-blue-500/60 transition-all hover:scale-105 flex items-center space-x-2"
            >
              <span>Start Building Free</span>
              <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
            </button>
            
            <button
              onClick={() => router.push('/auth/login')}
              className="px-8 py-4 rounded-xl bg-white/80 backdrop-blur-xl text-slate-800 font-bold text-lg shadow-lg border border-white hover:bg-white transition-all hover:scale-105"
            >
              View Demo
            </button>
          </motion.div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="relative z-10 container mx-auto px-6 py-12">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-5xl mx-auto"
        >
          {stats.map((stat, index) => (
            <div
              key={index}
              className="bg-white/60 backdrop-blur-xl rounded-2xl border border-white shadow-lg p-6 text-center hover:shadow-xl transition-shadow"
            >
              <stat.icon className="h-8 w-8 mx-auto mb-3 text-blue-600" />
              <div className="text-3xl font-black text-slate-800 mb-1">{stat.value}</div>
              <div className="text-sm font-medium text-slate-600">{stat.label}</div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Features Grid */}
      <div className="relative z-10 container mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-black text-slate-800 mb-4">
            Everything You Need
          </h2>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto">
            Powerful features to create, manage, and optimize your AI voice agents
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-8 max-w-6xl mx-auto">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.6 + index * 0.1 }}
              className="group relative overflow-hidden rounded-2xl border border-white/60 bg-white/60 backdrop-blur-xl p-8 shadow-lg hover:shadow-2xl transition-all hover:scale-105"
            >
              <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-gradient-to-br opacity-10 blur-3xl transition-opacity group-hover:opacity-20" 
                   style={{ backgroundImage: `linear-gradient(to bottom right, var(--tw-gradient-stops))` }} />
              
              <div className="relative z-10">
                <div className={`inline-flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br ${feature.gradient} text-white shadow-lg mb-4`}>
                  <feature.icon className="h-7 w-7" />
                </div>
                
                <h3 className="text-2xl font-bold text-slate-800 mb-3">
                  {feature.title}
                </h3>
                
                <p className="text-slate-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* CTA Section */}
      <div className="relative z-10 container mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1 }}
          className="max-w-4xl mx-auto bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-12 text-center shadow-2xl"
        >
          <Globe className="h-16 w-16 mx-auto mb-6 text-white opacity-90" />
          
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">
            Ready to Get Started?
          </h2>
          
          <p className="text-xl text-white/90 mb-8 max-w-2xl mx-auto">
            Join thousands of businesses using AI voice agents to transform their customer experience
          </p>
          
          <button
            onClick={() => router.push('/auth/signup')}
            className="px-10 py-4 rounded-xl bg-white text-blue-600 font-bold text-lg shadow-xl hover:shadow-2xl hover:scale-105 transition-all"
          >
            Create Your Free Account
          </button>
        </motion.div>
      </div>

      {/* Footer */}
      <div className="relative z-10 container mx-auto px-6 py-8 border-t border-slate-200">
        <p className="text-center text-slate-500">
          © 2025 VoiceAgent. All rights reserved.
        </p>
      </div>
    </div>
  )
}
