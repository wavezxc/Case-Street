import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { steamAPI } from './services/api';

// Steam Login Component
export const SteamLogin = ({ isLoggedIn, setIsLoggedIn, userInfo, setUserInfo }) => {
  const [loading, setLoading] = useState(false);

  const handleSteamLogin = async () => {
    try {
      setLoading(true);
      const response = await steamAPI.getSteamLoginUrl();
      window.location.href = response.data.login_url;
    } catch (error) {
      console.error('Steam login error:', error);
      alert('Ошибка входа через Steam');
      setLoading(false);
    }
  };

  if (isLoggedIn) {
    return (
      <div className="flex items-center space-x-3">
        <img 
          src={userInfo.avatar} 
          alt={userInfo.username}
          className="w-8 h-8 rounded-full"
        />
        <span className="text-gray-800 font-medium">{userInfo.username}</span>
        <button 
          onClick={() => {
            steamAPI.logout();
            setIsLoggedIn(false);
            setUserInfo(null);
            window.location.reload();
          }}
          className="text-gray-600 hover:text-gray-800 text-sm"
        >
          Выйти
        </button>
      </div>
    );
  }

  return (
    <button 
      onClick={handleSteamLogin}
      disabled={loading}
      className="bg-black text-white px-6 py-2 rounded-lg hover:bg-gray-800 transition-colors flex items-center space-x-2 disabled:opacity-50"
    >
      <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
      </svg>
      <span>{loading ? 'Подключение...' : 'Войти через Steam'}</span>
    </button>
  );
};

// Crypto Payment Modal Component
export const CryptoPaymentModal = ({ isOpen, onClose, balance, setBalance }) => {
  const [amount, setAmount] = useState('');
  const [selectedCrypto, setSelectedCrypto] = useState('USDT');
  const [promoCode, setPromoCode] = useState('');
  const [exchangeRate, setExchangeRate] = useState(90);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

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

  useEffect(() => {
    if (isOpen) {
      fetchExchangeRate();
    }
  }, [isOpen]);

  const fetchExchangeRate = async () => {
    try {
      const response = await steamAPI.getExchangeRate();
      setExchangeRate(response.data.usd_to_rub);
    } catch (error) {
      console.error('Error fetching exchange rate:', error);
    }
  };

  const handleCryptoPayment = async () => {
    if (!amount || parseFloat(amount) <= 0) {
      setError("Введите корректную сумму");
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await steamAPI.createCryptoPayment({
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
          const userResponse = await steamAPI.getProfile();
          if (userResponse.data.balance > balance) {
            clearInterval(checkPayment);
            paymentWindow.close();
            setBalance(userResponse.data.balance);
            setSuccess(`Оплата прошла успешно! Зачислено: ${(parseFloat(amount) * exchangeRate).toFixed(0)} ₽`);
            setTimeout(() => {
              onClose();
              setSuccess('');
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
    if (!promoCode || !amount || parseFloat(amount) <= 0) {
      setError("Введите промокод и сумму");
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await steamAPI.applyPromoCode({
        promo_code: promoCode,
        amount_rub: parseFloat(amount) * exchangeRate
      });

      setBalance(response.data.new_balance);
      setSuccess(`Промокод применен! Зачислено: ${response.data.added_amount_kopecks / 100} ₽`);
      setTimeout(() => {
        onClose();
        setSuccess('');
      }, 2000);

    } catch (error) {
      console.error("Error applying promocode:", error);
      setError(error.response?.data?.detail || "Неверный промокод");
    } finally {
      setLoading(false);
    }
  };

  const rubAmount = amount ? (parseFloat(amount) * exchangeRate).toFixed(0) : '0';

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-8 max-w-md w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Пополнение баланса</h2>
          <p className="text-gray-600">Выберите способ пополнения</p>
        </div>

        {/* Amount Input */}
        <div className="mb-6">
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
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent"
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
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-4">💰 Криптовалютная оплата</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Выберите криптовалюту
              </label>
              <select
                value={selectedCrypto}
                onChange={(e) => setSelectedCrypto(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black"
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
              className="w-full bg-black text-white py-3 px-4 rounded-lg font-semibold hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Создание платежа..." : "Оплатить криптовалютой"}
            </button>
          </div>
        </div>

        {/* Promocode */}
        <div className="mb-6">
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

        {/* Close Button */}
        <div className="text-center">
          <button
            onClick={() => {
              onClose();
              setError('');
              setSuccess('');
            }}
            className="text-gray-600 hover:text-gray-800 font-medium"
          >
            ✕ Закрыть
          </button>
        </div>
      </div>
    </div>
  );
};

// Updated Balance Component
export const BalanceComponent = ({ balance, setBalance }) => {
  const [showCryptoModal, setShowCryptoModal] = useState(false);

  const formatBalance = (amount) => {
    return (amount / 100).toFixed(0);
  };

  return (
    <>
      <div className="flex items-center space-x-3">
        <div className="text-gray-800 font-medium">
          Баланс: {formatBalance(balance)} ₽
        </div>
        <button 
          onClick={() => setShowCryptoModal(true)}
          className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors text-sm"
        >
          Пополнить
        </button>
      </div>

      {/* Crypto Payment Modal */}
      <CryptoPaymentModal
        isOpen={showCryptoModal}
        onClose={() => setShowCryptoModal(false)}
        balance={balance}
        setBalance={setBalance}
      />
    </>
  );
};

// Case Opening Modal Component
export const CaseOpeningModal = ({ isOpen, onClose, caseData, balance, setBalance }) => {
  const [isSpinning, setIsSpinning] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [spinPosition, setSpinPosition] = useState(0);

  const formatPrice = (price) => {
    return (price / 100).toFixed(0);
  };

  const handleOpenCase = async () => {
    if (balance < caseData.price) {
      alert('Недостаточно средств!');
      return;
    }

    try {
      setIsSpinning(true);
      setShowResult(false);
      setSpinPosition(0);

      // Start spinning animation
      const targetPosition = -(window.innerWidth * 2 + Math.random() * 500);
      setSpinPosition(targetPosition);

      // Make API call to open case
      const response = await steamAPI.openCase(caseData.id);
      
      if (response.data.success) {
        // Wait for animation to complete
        setTimeout(() => {
          setSelectedItem(response.data.item);
          setBalance(response.data.remaining_balance);
          setIsSpinning(false);
          setShowResult(true);
        }, 3000);
      }
    } catch (error) {
      console.error('Case opening error:', error);
      alert('Ошибка открытия кейса');
      setIsSpinning(false);
    }
  };

  const handleTakeToInventory = () => {
    // Item is already added to inventory by backend
    onClose();
    setShowResult(false);
    setSelectedItem(null);
    setIsSpinning(false);
    setSpinPosition(0);
  };

  const handleCloseModal = () => {
    onClose();
    setShowResult(false);
    setSelectedItem(null);
    setIsSpinning(false);
    setSpinPosition(0);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl p-8 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-800 mb-2">Открытие кейса</h2>
          <h3 className="text-xl text-gray-600">{caseData.name}</h3>
        </div>

        {/* Case Opening Animation */}
        <div className="mb-8">
          <div className="relative bg-gray-100 rounded-xl p-8 overflow-hidden">
            {/* Spinning Items */}
            <div className="flex items-center justify-center mb-6">
              <div className="relative w-full max-w-2xl h-32 bg-white rounded-lg border-2 border-gray-300 overflow-hidden">
                {/* Selection Indicator */}
                <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-1 h-full bg-red-500 z-10"></div>
                
                {/* Items Carousel */}
                <div 
                  className="flex items-center h-full transition-transform duration-3000 ease-out"
                  style={{
                    transform: `translateX(${spinPosition}px)`,
                    width: '2000px'
                  }}
                >
                  {/* Repeat items for continuous effect */}
                  {Array.from({length: 20}).map((_, index) => (
                    <div
                      key={index}
                      className="flex-shrink-0 w-24 h-24 m-2 rounded-lg bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center"
                    >
                      <div className="w-16 h-16 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
                        <div className="w-8 h-8 bg-white bg-opacity-40 rounded"></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Open Case Button */}
            {!isSpinning && !showResult && (
              <div className="text-center">
                <button
                  onClick={handleOpenCase}
                  className="bg-black text-white px-8 py-4 rounded-xl text-lg font-medium hover:bg-gray-800 transition-colors"
                >
                  Открыть кейс ({formatPrice(caseData.price)} ₽)
                </button>
              </div>
            )}

            {/* Spinning Text */}
            {isSpinning && (
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-800 animate-pulse">
                  Открываем кейс...
                </div>
                <div className="text-gray-600 mt-2">Ожидайте результат</div>
              </div>
            )}
          </div>
        </div>

        {/* Result */}
        {showResult && selectedItem && (
          <div className="bg-gray-50 rounded-xl p-8 mb-6">
            <div className="text-center">
              <h3 className="text-2xl font-bold text-gray-800 mb-4">Поздравляем! Вы получили:</h3>
              <div className="mb-4">
                <img 
                  src={selectedItem.image_url} 
                  alt={selectedItem.name}
                  className="w-32 h-32 mx-auto rounded-lg"
                />
              </div>
              <h4 className="text-xl font-bold text-gray-800 mb-2">{selectedItem.name}</h4>
              <p className="text-lg text-gray-600 mb-4">Стоимость: {formatPrice(selectedItem.price)} ₽</p>
              <div className="flex justify-center space-x-4">
                <button
                  onClick={handleTakeToInventory}
                  className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors font-medium"
                >
                  Забрать в инвентарь
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Close Button */}
        {!isSpinning && !showResult && (
          <div className="text-center">
            <button
              onClick={handleCloseModal}
              className="text-gray-600 hover:text-gray-800 font-medium"
            >
              ✕ Закрыть окно
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

// Inventory Page Component
export const InventoryPage = () => {
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      const response = await steamAPI.getInventory();
      setInventory(response.data.items || []);
    } catch (error) {
      console.error('Inventory error:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    return (price / 100).toFixed(0);
  };

  const calculateTotalValue = () => {
    return inventory.reduce((total, item) => total + item.price, 0);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-800">Загрузка инвентаря...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">Инвентарь</h1>
          <p className="text-gray-600 text-lg">
            Предметов: {inventory.length} | Общая стоимость: {formatPrice(calculateTotalValue())} ₽
          </p>
        </div>

        {inventory.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-gray-500 text-xl mb-4">Ваш инвентарь пуст</div>
            <p className="text-gray-400">Откройте кейсы, чтобы получить предметы</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {inventory.map((item, index) => (
              <div key={index} className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-lg transition-all">
                <div className="mb-4">
                  <img 
                    src={item.image_url} 
                    alt={item.name}
                    className="w-full h-48 object-cover rounded-lg"
                  />
                </div>
                <h3 className="text-gray-800 font-bold text-lg mb-2">{item.name}</h3>
                <p className="text-gray-600 text-sm mb-2">Редкость: {item.rarity}</p>
                <div className="bg-gray-100 text-gray-800 font-bold text-lg py-2 px-3 rounded-lg text-center">
                  {formatPrice(item.price)} ₽
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Header Component
export const Header = ({ isLoggedIn, setIsLoggedIn, userInfo, setUserInfo, balance, setBalance }) => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Главная' },
    { path: '/inventory', label: 'Инвентарь' },
    { path: '/upgrade', label: 'Апгрейд' },
    { path: '/contracts', label: 'Контракты' },
    { path: '/giveaways', label: 'Розыгрыши' },
    { path: '/tournaments', label: 'Турниры' }
  ];

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-40">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link to="/" className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-black text-white rounded-lg flex items-center justify-center">
              <span className="font-bold text-lg">CS</span>
            </div>
            <span className="text-gray-800 font-bold text-xl">Case Street</span>
          </Link>
          
          <nav className="flex space-x-6">
            {navItems.map(item => (
              <Link 
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  location.pathname === item.path 
                    ? 'bg-black text-white' 
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        
        <div className="flex items-center space-x-4">
          {isLoggedIn && (
            <BalanceComponent balance={balance} setBalance={setBalance} />
          )}
          <SteamLogin 
            isLoggedIn={isLoggedIn} 
            setIsLoggedIn={setIsLoggedIn}
            userInfo={userInfo}
            setUserInfo={setUserInfo}
          />
        </div>
      </div>
    </header>
  );
};

// Case Card Component
export const CaseCard = ({ caseData, balance, setBalance, isLoggedIn }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [showOpeningModal, setShowOpeningModal] = useState(false);

  const formatPrice = (price) => {
    return (price / 100).toFixed(0);
  };

  const handleOpenCase = () => {
    if (!isLoggedIn) {
      alert('Войдите через Steam для открытия кейсов!');
      return;
    }
    setShowOpeningModal(true);
  };

  return (
    <>
      <div 
        className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-all duration-300 cursor-pointer case-card"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="relative mb-4">
          <img 
            src={caseData.image} 
            alt={caseData.name}
            className="w-full h-48 object-cover rounded-lg"
          />
          {caseData.is_new && (
            <div className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded text-xs font-bold">
              NEW
            </div>
          )}
        </div>
        <div className="space-y-2">
          <h3 className="text-gray-800 font-bold text-lg">{caseData.name}</h3>
          <p className="text-gray-600 text-sm">{caseData.items} предметов</p>
          <div className="bg-gray-100 text-gray-800 font-bold text-xl py-3 px-4 rounded-lg text-center price-highlight">
            {formatPrice(caseData.price)} ₽
          </div>
          <button 
            onClick={handleOpenCase}
            className="w-full bg-black text-white py-3 rounded-lg hover:bg-gray-800 transition-colors font-medium btn-primary"
          >
            Открыть кейс
          </button>
        </div>
      </div>

      {/* Case Opening Modal */}
      <CaseOpeningModal
        isOpen={showOpeningModal}
        onClose={() => setShowOpeningModal(false)}
        caseData={caseData}
        balance={balance}
        setBalance={setBalance}
      />
    </>
  );
};

// Main Page Component
export const MainPage = ({ balance, setBalance, isLoggedIn }) => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCases();
  }, []);

  const fetchCases = async () => {
    try {
      const response = await steamAPI.getCases();
      setCases(response.data.cases || []);
    } catch (error) {
      console.error('Cases error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-800">Загрузка кейсов...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">Открывай кейсы и сражайся!</h1>
          <p className="text-gray-600 text-lg">Выбери свой кейс и попробуй удачу в битве за лучшие предметы</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {cases.map(caseData => (
            <CaseCard 
              key={caseData.id} 
              caseData={caseData} 
              balance={balance}
              setBalance={setBalance}
              isLoggedIn={isLoggedIn}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

// Upgrade Page Component
export const UpgradePage = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">Апгрейд предметов</h1>
          <p className="text-gray-600 text-lg">Улучшай свои предметы с шансом получить более ценные</p>
        </div>
        
        <div className="bg-white rounded-xl border border-gray-200 p-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
            <div className="text-center">
              <div className="w-32 h-32 bg-gray-100 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-gray-400">Выберите предмет</span>
              </div>
              <button className="bg-black text-white px-6 py-2 rounded-lg hover:bg-gray-800 transition-colors">
                Выбрать предмет
              </button>
            </div>
            
            <div className="text-center">
              <div className="text-4xl mb-4">→</div>
              <p className="text-gray-600">Апгрейд</p>
            </div>
            
            <div className="text-center">
              <div className="w-32 h-32 bg-gray-100 rounded-lg mx-auto mb-4 flex items-center justify-center">
                <span className="text-gray-400">Результат</span>
              </div>
              <div className="text-gray-600">Шанс успеха: 50%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Contracts Page Component
export const ContractsPage = () => {
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">Контракты</h1>
          <p className="text-gray-600 text-lg">Обменивай предметы на новые по контрактам</p>
        </div>
        
        <div className="bg-white rounded-xl border border-gray-200 p-8">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center">
                <span className="text-gray-400">Слот {i}</span>
              </div>
            ))}
          </div>
          
          <div className="text-center">
            <button className="bg-black text-white px-8 py-3 rounded-lg hover:bg-gray-800 transition-colors font-medium">
              Создать контракт
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// Giveaways Page Component
export const GiveawaysPage = () => {
  const giveaways = [
    { id: 1, title: 'AK-47 | Редлайн', participants: 1250, timeLeft: '2 дня' },
    { id: 2, title: 'AWP | Азимов', participants: 890, timeLeft: '5 часов' },
    { id: 3, title: 'M4A4 | Хаул', participants: 2100, timeLeft: '1 день' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">Розыгрыши</h1>
          <p className="text-gray-600 text-lg">Участвуй в розыгрышах и выигрывай ценные предметы</p>
        </div>
        
        <div className="space-y-6">
          {giveaways.map(giveaway => (
            <div key={giveaway.id} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-gray-800 mb-2">{giveaway.title}</h3>
                  <p className="text-gray-600">Участников: {giveaway.participants}</p>
                  <p className="text-gray-600">Осталось: {giveaway.timeLeft}</p>
                </div>
                <button className="bg-black text-white px-6 py-3 rounded-lg hover:bg-gray-800 transition-colors">
                  Участвовать
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Tournaments Page Component
export const TournamentsPage = () => {
  const tournaments = [
    { id: 1, name: '2x2 Wingman', prize: '10000 ₽', players: '64/64', status: 'Идет' },
    { id: 2, name: 'Solo Tournament', prize: '5000 ₽', players: '28/32', status: 'Регистрация' },
    { id: 3, name: 'Team Battle', prize: '25000 ₽', players: '12/16', status: 'Регистрация' }
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-6">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-800 mb-4">Турниры</h1>
          <p className="text-gray-600 text-lg">Соревнуйся с другими игроками и выигрывай призы</p>
        </div>
        
        <div className="space-y-6">
          {tournaments.map(tournament => (
            <div key={tournament.id} className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-gray-800 mb-2">{tournament.name}</h3>
                  <p className="text-gray-600">Призовой фонд: {tournament.prize}</p>
                  <p className="text-gray-600">Игроков: {tournament.players}</p>
                  <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                    tournament.status === 'Идет' 
                      ? 'bg-green-100 text-green-800'
                      : 'bg-blue-100 text-blue-800'
                  }`}>
                    {tournament.status}
                  </span>
                </div>
                <button className="bg-black text-white px-6 py-3 rounded-lg hover:bg-gray-800 transition-colors">
                  {tournament.status === 'Идет' ? 'Смотреть' : 'Участвовать'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};