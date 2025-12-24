//
//  ContentView.swift
//  FinanceKitSync
//
//  Created by Samson Ayeni on 12/24/25.
//


import SwiftUI
import FinanceKit
import FinanceKitUI

// MARK: - Export Model (JSON-safe)
struct ExportTransaction: Codable {
    let external_id: String
    let name: String
    let amount: Decimal
    let direction: String
    let date: Date
}
enum Direction: String, Codable {
    case IN
    case OUT
}

struct ContentView: View {

    @State private var isSyncing = false
    @State private var selectedTransactions: [FinanceKit.Transaction] = []
    @State private var statusMessage: String?

    private let financeStore = FinanceStore.shared

    var body: some View {
        VStack(spacing: 16) {

            // Header
            Text("Transactions")
                .font(.title2)
                .fontWeight(.semibold)

            // Action Row
            HStack(spacing: 12) {

                TransactionPicker(
                    selection: $selectedTransactions,
                    label: {
                        Label("Select", systemImage: "list.bullet")
                    }
                )
                .buttonStyle(.bordered)

                Button {
                    Task {
                        await syncTransactions()
                    }
                } label: {
                    if isSyncing {
                        ProgressView()
                    } else {
                        Label("Sync", systemImage: "arrow.triangle.2.circlepath")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isSyncing || selectedTransactions.isEmpty)
            }

            if let statusMessage {
                Text(statusMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: 420)
        .frame(maxWidth: .infinity, alignment: .center)
        .padding()
    }

    // MARK: - FinanceKit Flow
    private func syncTransactions() async {
        if selectedTransactions.isEmpty {
            return
        }

        isSyncing = true
        statusMessage = "Syncing transactions…"

        let exported = mapTransactions(selectedTransactions)

        guard let url = URL(string: "http://samsons-macbook-air.local:8000/transactions") else {
            statusMessage = "Invalid backend URL"
            isSyncing = false
            return
        }

        do {
            let jsonData = try JSONEncoder.withISO8601.encode(exported)

            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = jsonData

            let (_, response) = try await URLSession.shared.data(for: request)

            if let httpResponse = response as? HTTPURLResponse,
               !(200...299).contains(httpResponse.statusCode) {
                statusMessage = "Sync failed (HTTP \(httpResponse.statusCode))"
            } else {
                statusMessage = "Synced \(exported.count) transactions"
            }
        } catch {
            statusMessage = "Sync error: \(error.localizedDescription)"
        }

        isSyncing = false
    }

    // MARK: - Mapping
    private func mapTransactions(_ transactions: [FinanceKit.Transaction]) -> [ExportTransaction] {
        transactions.map { tx in
            return ExportTransaction(
                external_id: tx.id.uuidString,
                name: tx.merchantName
                    ?? tx.transactionDescription,
                amount: tx.transactionAmount.amount,
                direction: tx.creditDebitIndicator == .credit ? "IN" : "OUT",
                date: tx.transactionDate
            )
        }
    }
}

// MARK: - JSON Encoder Helper
extension JSONEncoder {
    static let withISO8601: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601
        return encoder
    }()
}

#Preview {
    ContentView()
}
