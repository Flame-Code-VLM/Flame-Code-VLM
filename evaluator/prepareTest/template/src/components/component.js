import "./style.css"
import React, { useState, useEffect } from 'react';

const LuxuryTravelApp = () => {
  const [destinations, setDestinations] = useState([
    { name: 'Maldives', roomsAvailable: 5, category: 'beach', price: 1200 },
    { name: 'Bora Bora', roomsAvailable: 3, category: 'beach', price: 1500 },
    { name: 'Santorini', roomsAvailable: 7, category: 'urban', price: 1000 }
  ]);
  const [selectedDestination, setSelectedDestination] = useState('Maldives');
  const [guests, setGuests] = useState(2);
  const [checkIn, setCheckIn] = useState('2024-05-01');
  const [checkOut, setCheckOut] = useState('2024-05-07');
  const [availableRooms, setAvailableRooms] = useState(5);
  const [specialOffers, setSpecialOffers] = useState(['Complimentary Spa', 'Private Yacht Tour']);
  const [mapCenter, setMapCenter] = useState([0, 0]);
  const [filterCategory, setFilterCategory] = useState('all');
  const [recommendations, setRecommendations] = useState([]);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');

  useEffect(() => {
    const filteredDestinations = filterCategory === 'all' ? destinations : destinations.filter(d => d.category === filterCategory);
    setRecommendations(filteredDestinations.slice(0, 3));
  }, [filterCategory, destinations]);

  const handleBooking = () => {
    const updatedDestinations = destinations.map(destination =>
      destination.name === selectedDestination ? { ...destination, roomsAvailable: destination.roomsAvailable - 1 } : destination
    );
    setDestinations(updatedDestinations);
    setAvailableRooms(updatedDestinations.find(d => d.name === selectedDestination).roomsAvailable);
  };

  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (chatInput.trim()) {
      setChatMessages([...chatMessages, { text: chatInput, sender: 'user' }]);
      setChatInput('');
      setTimeout(() => {
        setChatMessages([...chatMessages, { text: 'Thank you for your message. We will get back to you shortly.', sender: 'bot' }]);
      }, 1000);
    }
  };

  return (
    <div className='container'>
      <div className='destination-showcase'>
        <h2>Luxury Destinations</h2>
        <div className='map-container'>
          <div className='map-marker'>Maldives: 5 rooms left</div>
          <div className='map-marker'>Bora Bora: 3 rooms left</div>
          <div className='map-marker'>Santorini: 7 rooms left</div>
        </div>
        <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
          <option value='all'>All Categories</option>
          <option value='beach'>Beach Resorts</option>
          <option value='urban'>Urban Luxury</option>
        </select>
        {destinations.map((destination, index) => (
          <div key={index} className='showcase-item'>
            <h3>{destination.name}</h3>
            <p>Rooms Available: {destination.roomsAvailable}</p>
          </div>
        ))}
      </div>
      <div className='booking-form'>
        <h2>Book Your Stay</h2>
        <div className='form-group'>
          <label>Destination</label>
          <select value={selectedDestination} onChange={(e) => setSelectedDestination(e.target.value)}>
            {destinations.map((destination, index) => (
              <option key={index} value={destination.name}>{destination.name}</option>
            ))}
          </select>
        </div>
        <div className='form-group'>
          <label>Check-in Date</label>
          <input type='date' value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
        </div>
        <div className='form-group'>
          <label>Check-out Date</label>
          <input type='date' value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
        </div>
        <div className='form-group'>
          <label>Number of Guests</label>
          <input type='number' value={guests} onChange={(e) => setGuests(Number(e.target.value))} />
        </div>
        <button onClick={handleBooking}>Confirm Booking</button>
      </div>
      <div className='availability-dashboard'>
        <h2>Real-Time Availability</h2>
        <div className='availability-item'>
          <h4>Rooms Left: {availableRooms}</h4>
        </div>
        <div className='availability-item'>
          <h4>Special Offers</h4>
          <ul>
            {specialOffers.map((offer, index) => <li key={index}>{offer}</li>)}
          </ul>
        </div>
        <h2>Recommended for You</h2>
        <div className='recommendation-carousel'>
          {recommendations.map((rec, index) => (
            <div key={index} className='recommendation-item'>
              <h3>{rec.name}</h3>
              <p>Starting at ${rec.price}</p>
            </div>
          ))}
        </div>
      </div>
      <div className='chat-button' onClick={() => setIsChatOpen(!isChatOpen)}>💬</div>
      {isChatOpen && (
        <div className='chat-window'>
          <div className='chat-messages'>
            {chatMessages.map((msg, index) => (
              <div key={index} style={{ textAlign: msg.sender === 'user' ? 'right' : 'left' }}>
                {msg.text}
              </div>
            ))}
          </div>
          <form onSubmit={handleChatSubmit}>
            <input
              type='text'
              className='chat-input'
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder='Type a message...'
            />
          </form>
        </div>
      )}
    </div>
  );
};

export default LuxuryTravelApp;