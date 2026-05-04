import Foundation

struct Signal: Identifiable, Codable {
    let id: String
    let symbol: String
    let signalType: SignalType
    let strength: SignalStrength
    let currentPrice: Double
    let suggestedStrike: Double?
    let stopLoss: Double?
    let targetPrice: Double?
    let riskRewardRatio: Double?
    let rationale: String
    let timestamp: Date

    enum CodingKeys: String, CodingKey {
        case id, symbol, rationale, timestamp
        case signalType = "signal_type"
        case strength = "strength_name"
        case currentPrice = "current_price"
        case suggestedStrike = "suggested_strike"
        case stopLoss = "stop_loss"
        case targetPrice = "target_price"
        case riskRewardRatio = "risk_reward_ratio"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        symbol = try container.decode(String.self, forKey: .symbol)
        signalType = try container.decode(SignalType.self, forKey: .signalType)
        currentPrice = try container.decode(Double.self, forKey: .currentPrice)
        suggestedStrike = try container.decodeIfPresent(Double.self, forKey: .suggestedStrike)
        stopLoss = try container.decodeIfPresent(Double.self, forKey: .stopLoss)
        targetPrice = try container.decodeIfPresent(Double.self, forKey: .targetPrice)
        riskRewardRatio = try container.decodeIfPresent(Double.self, forKey: .riskRewardRatio)
        rationale = try container.decode(String.self, forKey: .rationale)
        id = (try? container.decode(String.self, forKey: .id)) ?? UUID().uuidString
        timestamp = (try? container.decode(Date.self, forKey: .timestamp)) ?? Date()

        let strengthString = try container.decode(String.self, forKey: .strength)
        strength = SignalStrength(rawValue: strengthString.lowercased()) ?? .moderate
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(symbol, forKey: .symbol)
        try container.encode(signalType, forKey: .signalType)
        try container.encode(strength.rawValue, forKey: .strength)
        try container.encode(currentPrice, forKey: .currentPrice)
        try container.encodeIfPresent(suggestedStrike, forKey: .suggestedStrike)
        try container.encodeIfPresent(stopLoss, forKey: .stopLoss)
        try container.encodeIfPresent(targetPrice, forKey: .targetPrice)
        try container.encodeIfPresent(riskRewardRatio, forKey: .riskRewardRatio)
        try container.encode(rationale, forKey: .rationale)
        try container.encode(timestamp, forKey: .timestamp)
    }
}

enum SignalType: String, Codable {
    case longCall = "LONG_CALL"
    case longPut = "LONG_PUT"
    case shortCall = "SHORT_CALL"
    case shortPut = "SHORT_PUT"
    case bullishSwing = "BULLISH_SWING"
    case bearishSwing = "BEARISH_SWING"
    case volatilityPlay = "VOLATILITY_PLAY"

    var icon: String {
        switch self {
        case .longCall, .bullishSwing: return "arrow.up.right"
        case .longPut, .bearishSwing: return "arrow.down.right"
        case .shortCall: return "arrow.down.left"
        case .shortPut: return "arrow.up.left"
        case .volatilityPlay: return "waveform.path.ecg"
        }
    }

    var color: String {
        switch self {
        case .longCall, .bullishSwing, .shortPut: return "green"
        case .longPut, .bearishSwing, .shortCall: return "red"
        case .volatilityPlay: return "purple"
        }
    }
}

enum SignalStrength: String, Codable {
    case weak
    case moderate
    case strong
    case veryStrong = "very_strong"

    var label: String {
        switch self {
        case .weak: return "Weak"
        case .moderate: return "Moderate"
        case .strong: return "Strong"
        case .veryStrong: return "Very Strong"
        }
    }

    var dots: Int {
        switch self {
        case .weak: return 1
        case .moderate: return 2
        case .strong: return 3
        case .veryStrong: return 4
        }
    }
}
