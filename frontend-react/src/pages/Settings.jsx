import { useState } from 'react';
import { Save, Moon, Sun, Sparkles } from 'lucide-react';
import { authAPI } from '../api';
import { useUser } from '../UserContext';

const PERSONALITIES = [
    { value: 'friendly', label: 'Paige - Friendly', emoji: '😊', desc: 'Warm, uses emojis 📚' },
    { value: 'professional', label: 'Dr. Morgan - Professional', emoji: '🎩', desc: 'Formal, scholarly' },
    { value: 'flirty', label: 'Alex - Flirty', emoji: '😏', desc: 'Charming, playful' },
    { value: 'mentor', label: 'Prof. Wells - Mentor', emoji: '🧙', desc: 'Wise, guiding' },
    { value: 'sarcastic', label: 'Max - Sarcastic', emoji: '😎', desc: 'Witty, dry humor' },
];

export default function Settings() {
    const { user, theme, setTheme, personality, setPersonality } = useUser();
    const [saved, setSaved] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSave = async () => {
        setLoading(true);
        try {
            if (user) {
                await authAPI.updatePreferences(user.id, { theme, personality });
            }
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        } catch (error) {
            console.error('Failed to save settings:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="pt-24 px-6 max-w-2xl mx-auto pb-12">
            <h1 className="text-3xl font-bold mb-2">⚙️ Settings</h1>
            <p className="text-gray-400 mb-8">Customize your experience</p>

            <div className="space-y-8">
                {/* Theme */}
                <div className="glass rounded-2xl p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
                        Appearance
                    </h2>
                    <div className="flex gap-4">
                        <button
                            onClick={() => setTheme('dark')}
                            className={`flex-1 p-4 rounded-xl border-2 transition-all ${theme === 'dark'
                                    ? 'border-red-500 bg-red-500/10'
                                    : 'border-white/10 hover:border-white/30'
                                }`}
                        >
                            <Moon size={24} className="mx-auto mb-2" />
                            <p className="font-medium">Dark Mode</p>
                        </button>
                        <button
                            onClick={() => setTheme('light')}
                            className={`flex-1 p-4 rounded-xl border-2 transition-all ${theme === 'light'
                                    ? 'border-red-500 bg-red-500/10'
                                    : 'border-white/10 hover:border-white/30'
                                }`}
                        >
                            <Sun size={24} className="mx-auto mb-2" />
                            <p className="font-medium">Light Mode</p>
                        </button>
                    </div>
                </div>

                {/* Personality */}
                <div className="glass rounded-2xl p-6">
                    <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
                        <Sparkles size={20} />
                        Assistant Personality
                    </h2>
                    <p className="text-sm text-gray-400 mb-4">Choose how your librarian talks to you</p>
                    <div className="grid gap-3">
                        {PERSONALITIES.map((p) => (
                            <button
                                key={p.value}
                                onClick={() => setPersonality(p.value)}
                                className={`flex items-center gap-4 p-4 rounded-xl border-2 text-left transition-all ${personality === p.value
                                        ? 'border-red-500 bg-red-500/10'
                                        : 'border-white/10 hover:border-white/30'
                                    }`}
                            >
                                <span className="text-3xl">{p.emoji}</span>
                                <div>
                                    <p className="font-medium">{p.label}</p>
                                    <p className="text-sm text-gray-400">{p.desc}</p>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Save Button */}
                <button
                    onClick={handleSave}
                    disabled={loading || saved}
                    className="w-full py-4 btn-gradient rounded-xl font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
                >
                    {saved ? (
                        <>✓ Saved!</>
                    ) : loading ? (
                        <>Saving...</>
                    ) : (
                        <>
                            <Save size={18} />
                            Save Settings
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
