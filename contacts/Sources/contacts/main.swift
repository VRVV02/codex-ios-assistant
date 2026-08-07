import Contacts
import Darwin
import Foundation

private let usage = "Usage: contacts search <query>"

private struct ContactMatch {
    let contact: CNContact
    let score: Int
}

@main
struct ContactsCommand {
    static func main() async {
        let arguments = Array(CommandLine.arguments.dropFirst())

        if arguments == ["--help"] || arguments == ["-h"] {
            print(usage)
            return
        }

        guard arguments.first == "search", arguments.count > 1 else {
            fail(usage)
        }

        let query = arguments.dropFirst()
            .joined(separator: " ")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        guard !query.isEmpty else {
            fail(usage)
        }

        let store = CNContactStore()
        await requestAccess(to: store)

        let keys: [CNKeyDescriptor] = [
            CNContactFormatter.descriptorForRequiredKeys(for: .fullName),
            CNContactOrganizationNameKey as CNKeyDescriptor,
            CNContactEmailAddressesKey as CNKeyDescriptor,
            CNContactPhoneNumbersKey as CNKeyDescriptor,
        ]

        do {
            let request = CNContactFetchRequest(keysToFetch: keys)
            request.unifyResults = true

            var matches: [ContactMatch] = []
            try store.enumerateContacts(with: request) { contact, _ in
                if let match = match(contact, query: query) {
                    matches.append(match)
                }
            }

            matches.sort {
                if $0.score != $1.score { return $0.score < $1.score }
                return displayName(for: $0.contact)
                    .localizedStandardCompare(displayName(for: $1.contact)) == .orderedAscending
            }

            let results = matches.prefix(50)

            guard !results.isEmpty else {
                print("No contacts found.")
                return
            }

            for (index, result) in results.enumerated() {
                let contact = result.contact
                if index > 0 { print() }
                print(displayName(for: contact))

                for email in contact.emailAddresses {
                    print("  \(email.value)")
                }

                for phone in contact.phoneNumbers {
                    print("  \(e164(phone.value.stringValue))")
                }
            }

            if matches.count > results.count {
                print("\nShowing 50 of \(matches.count) matches.")
            }
        } catch {
            fail("Could not read contacts: \(error.localizedDescription)")
        }
    }

    private static func requestAccess(to store: CNContactStore) async {
        switch CNContactStore.authorizationStatus(for: .contacts) {
        case .authorized:
            return
        case .notDetermined:
            do {
                guard try await store.requestAccess(for: .contacts) else {
                    fail(permissionMessage)
                }
            } catch {
                fail("Could not request Contacts access: \(error.localizedDescription)")
            }
        case .denied, .restricted:
            fail(permissionMessage)
        @unknown default:
            fail(permissionMessage)
        }
    }

    private static func displayName(for contact: CNContact) -> String {
        if let name = CNContactFormatter.string(from: contact, style: .fullName), !name.isEmpty {
            return name
        }
        if !contact.organizationName.isEmpty {
            return contact.organizationName
        }
        return "Unnamed contact"
    }

    private static func match(_ contact: CNContact, query: String) -> ContactMatch? {
        var scores: [Int] = []

        if let score = textMatchScore(displayName(for: contact), query: query) {
            scores.append(score)
        }

        if !contact.organizationName.isEmpty,
           let score = textMatchScore(contact.organizationName, query: query) {
            scores.append(score)
        }

        for email in contact.emailAddresses {
            let value = email.value as String
            if let score = textMatchScore(value, query: query) {
                scores.append(score)
            }
        }

        if isPhoneQuery(query) {
            let queryDigits = digits(in: query)
            for phone in contact.phoneNumbers {
                let value = e164(phone.value.stringValue)
                if let score = textMatchScore(digits(in: value), query: queryDigits) {
                    scores.append(score)
                }
            }
        }

        guard let score = scores.min() else { return nil }
        return ContactMatch(contact: contact, score: score)
    }

    private static func textMatchScore(_ value: String, query: String) -> Int? {
        let normalizedValue = value.folding(
            options: [.caseInsensitive, .diacriticInsensitive],
            locale: .current
        )
        let normalizedQuery = query.folding(
            options: [.caseInsensitive, .diacriticInsensitive],
            locale: .current
        )

        if normalizedValue == normalizedQuery { return 0 }
        if normalizedValue.hasPrefix(normalizedQuery) { return 1 }
        if normalizedValue.contains(normalizedQuery) { return 2 }
        return nil
    }

    private static func isPhoneQuery(_ query: String) -> Bool {
        let allowed = CharacterSet(charactersIn: "+0123456789().- ")
        let scalars = query.unicodeScalars
        return scalars.filter { CharacterSet.decimalDigits.contains($0) }.count >= 3
            && scalars.allSatisfy { allowed.contains($0) }
    }

    private static func digits(in value: String) -> String {
        value.compactMap(\.wholeNumberValue).map(String.init).joined()
    }

    private static func e164(_ phoneNumber: String) -> String {
        let trimmed = phoneNumber.trimmingCharacters(in: .whitespacesAndNewlines)
        let digits = digits(in: trimmed)

        if trimmed.hasPrefix("+") {
            return "+\(digits)"
        }

        if trimmed.hasPrefix("00") {
            return "+\(digits.dropFirst(2))"
        }

        return digits
    }

    private static var permissionMessage: String {
        "Contacts access is required. Enable it in System Settings > Privacy & Security > Contacts."
    }

    private static func fail(_ message: String) -> Never {
        FileHandle.standardError.write(Data("\(message)\n".utf8))
        exit(EXIT_FAILURE)
    }
}
