import React, { useEffect, useState } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Поддерживаемые криптовалюты
const SUPPORTED_CRYPTO = [
  { code: "USDT", name: "Tether (USDT)" },
  { code: "TON", name: "Toncoin (TON)" },
  { code: "TRX", name: "TRON (TRX)" },
  { code: "BTC", name: "Bitcoin (BTC)" },
  { code: "ETH", name: "Ethereum (ETH)" },
  { code: "LTC", name: "Litecoin (LTC)" },
  { code: "NOT", name: "Notcoin (NOT)" },
  { code: "BNB", name: "BNB (BNB)" }
];

const Home = () => {
  const [user, setUser] = useState(null);
  const [exchangeRate, setExchangeRate] = useState(90);
  const [loading, setLoading] = useState(false);

  // Создаем или получаем пользователя
  const initializeUser = async () => {
    try {
      const username = "demo_user"; // В реальной системе это будет из аутентификации
      const response = await axios.post(`${API}/users`, { username });
      setUser(response.data);
    } catch (error) {
      console.error("Error initializing user:", error);
    }
  };

  // Получаем курс валют
  const getExchangeRate = async () => {
    try {
      const response = await axios.get(`${API}/exchange-rate`);
      setExchangeRate(response.data.usd_to_rub);
    } catch (error) {
      console.error("Error getting exchange rate:", error);
    }
  };

  useEffect(() => {
    initializeUser();
    getExchangeRate();
  }, []);

  const refreshUser = async () => {
    if (user) {
      try {
        const response = await axios.get(`${API}/users/${user.id}`);
        setUser(response.data);
      } catch (error) {
        console.error("Error refreshing user:", error);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-md mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              💰 Crypto Wallet
            </h1>
            <p className="text-gray-600">Пополните баланс криптовалютой</p>
          </div>

          {/* Balance Card */}
          {user && (
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <div className="text-center">
                <h2 className="text-lg font-semibold text-gray-700 mb-2">
                  Ваш баланс
                </h2>
                <div className="text-4xl font-bold text-indigo-600 mb-4">
                  {user.balance_rub.toFixed(2)} ₽
                </div>
                <button
                  onClick={refreshUser}
                  className="text-sm text-indigo-500 hover:text-indigo-700 underline"
                >
                  Обновить баланс
                </button>
              </div>
            </div>
          )}

          {/* Exchange Rate Info */}
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between text-sm">
              <span className="text-yellow-800">Курс USD/RUB:</span>
              <span className="font-semibold text-yellow-900">
                {exchangeRate.toFixed(2)} ₽
              </span>
            </div>
          </div>

          {/* Top-up button */}
          <div className="space-y-4">
            <button
              onClick={() => window.location.href = '/topup'}
              className="w-full bg-indigo-600 text-white py-4 px-6 rounded-xl font-semibold text-lg hover:bg-indigo-700 transition-colors shadow-lg"
            >
              🚀 Пополнить баланс
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const TopUpPage = () => {
  const [user, setUser] = useState(null);
  const [amount, setAmount] = useState('');
  const [selectedCrypto, setSelectedCrypto] = useState('USDT');
  const [promoCode, setPromoCode] = useState('');
  const [exchangeRate, setExchangeRate] = useState(90);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    const initializePage = async () => {
      try {
        // Получить пользователя
        const username = "demo_user";
        const userResponse = await axios.post(`${API}/users`, { username });
        setUser(userResponse.data);

        // Получить курс валют
        const rateResponse = await axios.get(`${API}/exchange-rate`);
        setExchangeRate(rateResponse.data.usd_to_rub);
      } catch (error) {
        console.error("Error initializing topup page:", error);
        setError("Ошибка загрузки данных");
      }
    };

    initializePage();
  }, []);

  const handleCryptoPayment = async () => {
    if (!user || !amount || parseFloat(amount) <= 0) {
      setError("Введите корректную сумму");
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API}/create-payment`, {
        user_id: user.id,
        amount_usd: parseFloat(amount),
        crypto_currency: selectedCrypto
      });

      // Открыть окно оплаты
      const paymentWindow = window.open(
        response.data.pay_url,
        'payment',
        'width=600,height=700,scrollbars=yes,resizable=yes'
      );

      // Проверять статус оплаты
      const checkPayment = setInterval(async () => {
        try {
          const userResponse = await axios.get(`${API}/users/${user.id}`);
          if (userResponse.data.balance_rub > user.balance_rub) {
            clearInterval(checkPayment);
            paymentWindow.close();
            setSuccess(`Оплата прошла успешно! Зачислено: ${(parseFloat(amount) * exchangeRate).toFixed(2)} ₽`);
            setTimeout(() => {
              window.location.href = '/';
            }, 3000);
          }
        } catch (error) {
          console.error("Error checking payment:", error);
        }
      }, 3000);

      // Остановить проверку через 10 минут
      setTimeout(() => {
        clearInterval(checkPayment);
      }, 600000);

    } catch (error) {
      console.error("Error creating payment:", error);
      setError("Ошибка создания платежа");
    } finally {
      setLoading(false);
    }
  };

  const handlePromoCode = async () => {
    if (!user || !promoCode || !amount || parseFloat(amount) <= 0) {
      setError("Введите промокод и сумму");
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API}/promocode`, {
        user_id: user.id,
        promo_code: promoCode,
        amount_rub: parseFloat(amount) * exchangeRate
      });

      setSuccess(`Промокод применен! Зачислено: ${response.data.added_amount.toFixed(2)} ₽`);
      setTimeout(() => {
        window.location.href = '/';
      }, 2000);

    } catch (error) {
      console.error("Error applying promocode:", error);
      setError(error.response?.data?.detail || "Неверный промокод");
    } finally {
      setLoading(false);
    }
  };

  const rubAmount = amount ? (parseFloat(amount) * exchangeRate).toFixed(2) : '0.00';

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-pink-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-md mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <button
              onClick={() => window.location.href = '/'}
              className="text-indigo-600 hover:text-indigo-800 mb-4 inline-flex items-center"
            >
              ← Назад
            </button>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">
              💳 Пополнение
            </h1>
            <p className="text-gray-600">Выберите способ пополнения</p>
          </div>

          {/* Amount Input */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">Сумма пополнения</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Сумма в долларах (USD)
                </label>
                <input
                  type="number"
                  min="1"
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  placeholder="0.00"
                />
              </div>
              <div className="bg-gray-50 p-3 rounded-lg">
                <div className="text-sm text-gray-600">
                  Курс: 1 USD = {exchangeRate.toFixed(2)} ₽
                </div>
                <div className="text-lg font-semibold text-gray-800">
                  К зачислению: {rubAmount} ₽
                </div>
              </div>
            </div>
          </div>

          {/* Crypto Payment */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">💰 Криптовалютная оплата</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Выберите криптовалюту
                </label>
                <select
                  value={selectedCrypto}
                  onChange={(e) => setSelectedCrypto(e.target.value)}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                  {SUPPORTED_CRYPTO.map(crypto => (
                    <option key={crypto.code} value={crypto.code}>
                      {crypto.name}
                    </option>
                  ))}
                </select>
              </div>
              <button
                onClick={handleCryptoPayment}
                disabled={loading || !amount || parseFloat(amount) <= 0}
                className="w-full bg-indigo-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Создание платежа..." : "Оплатить криптовалютой"}
              </button>
            </div>
          </div>

          {/* Promocode */}
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h3 className="text-lg font-semibold mb-4">🎫 Промокод</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Введите промокод
                </label>
                <input
                  type="text"
                  value={promoCode}
                  onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  placeholder="Промокод"
                />
              </div>
              <button
                onClick={handlePromoCode}
                disabled={loading || !promoCode || !amount || parseFloat(amount) <= 0}
                className="w-full bg-green-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? "Применение..." : "Применить промокод"}
              </button>
            </div>
          </div>

          {/* Messages */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-800">{error}</p>
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <p className="text-green-800">{success}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const PaymentSuccess = () => {
  useEffect(() => {
    // Закрыть окно через 2 секунды
    setTimeout(() => {
      window.close();
    }, 2000);
  }, []);

  return (
    <div className="min-h-screen bg-green-50 flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl mb-4">✅</div>
        <h1 className="text-2xl font-bold text-green-800 mb-2">
          Оплата прошла успешно!
        </h1>
        <p className="text-green-600">
          Ваш баланс будет обновлен в течение нескольких секунд
        </p>
        <p className="text-sm text-gray-500 mt-4">
          Это окно закроется автоматически...
        </p>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/topup" element={<TopUpPage />} />
          <Route path="/payment-success" element={<PaymentSuccess />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
