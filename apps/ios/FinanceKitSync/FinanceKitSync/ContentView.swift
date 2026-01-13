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
struct ExportAccountInfo: Codable {
    let id: String
    let display_name: String
    let available_balance: Decimal?
    let institution_name: String?
    let card_last4: String?
}

struct ExportTransaction: Codable {
    let id: String
    let account_id: String
    let name: String
    let amount: Decimal
    let direction: Direction
    let date: Date
}

struct ExportAccountTransactions: Codable {
    let account: ExportAccountInfo
    let transactions: [ExportTransaction]
}
enum Direction: String, Codable {
    case IN
    case OUT
}

struct ContentView: View {

    @State private var isSyncing = false
    @State private var selectedTransactions: [FinanceKit.Transaction] = []
    @State private var statusMessage: String?

    @AppStorage("backend_url") private var backendURL: String = "http://samsons-macbook-air.local:8000/"

    private let financeStore = FinanceStore.shared

    var body: some View {
        VStack(spacing: 16) {

            // Header
            Text("Transactions")
                .font(.title2)
                .fontWeight(.semibold)

            TextField("Backend URL", text: $backendURL)
                .textFieldStyle(.roundedBorder)
                .keyboardType(.URL)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()

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

        do {
            let accounts = try await financeStore.accounts()
            let exported = mapAccountTransactions(selectedTransactions, accounts: accounts)

            guard let url = URL(string: backendURL) else {
                statusMessage = "Invalid backend URL"
                isSyncing = false
                return
            }

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
                let transactionCount = exported.reduce(0) { $0 + $1.transactions.count }
                statusMessage = "Synced \(transactionCount) transactions"
            }
        } catch {
            statusMessage = "Sync error: \(error.localizedDescription)"
        }

        isSyncing = false
    }

    // MARK: - Mapping
    private func mapAccountTransactions(
        _ transactions: [FinanceKit.Transaction],
        accounts: [FinanceKit.Account]
    ) -> [ExportAccountTransactions] {
        let accountInfoById = Dictionary(
            uniqueKeysWithValues: accounts.map { account in
                (account.id, mapAccountInfo(account))
            }
        )

        return Dictionary(grouping: transactions, by: { $0.accountID })
            .map { accountID, groupedTransactions in
                let info = accountInfoById[accountID]
                    ?? ExportAccountInfo(
                        id: accountID.uuidString,
                        display_name: "Unknown Account",
                        available_balance: nil,
                        institution_name: nil,
                        card_last4: nil
                    )
                return ExportAccountTransactions(
                    account: info,
                    transactions: groupedTransactions.map(mapTransaction)
                )
            }
    }

    private func mapAccountInfo(_ account: FinanceKit.Account) -> ExportAccountInfo {
        ExportAccountInfo(
            id: account.id.uuidString,
            display_name: account.displayName,
            available_balance: account.availableBalance?.amount,
            institution_name: account.institutionName,
            card_last4: account.cardLast4
        )
    }

    private func mapTransaction(_ tx: FinanceKit.Transaction) -> ExportTransaction {
        ExportTransaction(
            id: tx.id.uuidString,
            account_id: tx.accountID.uuidString,
            name: tx.merchantName
                ?? tx.transactionDescription,
            amount: tx.transactionAmount.amount,
            direction: tx.creditDebitIndicator == .credit ? Direction.IN : Direction.OUT,
            date: tx.transactionDate
        )
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
