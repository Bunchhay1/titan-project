package com.titan.promotions.controller;

import com.titan.promotions.event.TransactionCompletedEvent;
import com.titan.promotions.service.DepositPromotionService;
import com.titan.promotions.service.DepositPromotionService.CampaignStatusDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * DepositPromotionController
 *
 * REST endpoints for the "Deposit $100 → Bonus $2" promotion campaign.
 *
 * Base path  : /promotions/deposit
 * Endpoints  :
 *   POST /promotions/deposit/apply    – manually trigger deposit promotion evaluation
 *   GET  /promotions/deposit/status   – check campaign status and window info
 */
@RestController
@RequestMapping("/promotions/deposit")
@Slf4j
@RequiredArgsConstructor
public class DepositPromotionController {

    private final DepositPromotionService depositPromotionService;

    // ─────────────────────────────────────────────────────────────────────
    // POST /promotions/deposit/apply
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Manually evaluate and apply the deposit promotion for a given transaction.
     *
     * Request body example:
     * {
     *   "transactionId": "1001",
     *   "type": "DEPOSIT",
     *   "amount": 150.00,
     *   "currency": "USD",
     *   "metadata": { "accountId": "42" }
     * }
     *
     * Response:
     *   200 OK   → { "applied": true,  "bonus": 2.00, "message": "..." }
     *   200 OK   → { "applied": false, "bonus": 0,    "message": "..." }
     *   400 Bad Request → when required fields are missing
     */
    @PostMapping("/apply")
    public ResponseEntity<Map<String, Object>> applyDepositPromotion(
            @RequestBody TransactionCompletedEvent event) {

        // Basic input validation
        if (event == null) {
            return ResponseEntity.badRequest()
                    .body(errorResponse("Request body is required"));
        }
        if (event.getAmount() == null) {
            return ResponseEntity.badRequest()
                    .body(errorResponse("Field 'amount' is required"));
        }
        if (event.getTransactionId() == null || event.getTransactionId().isBlank()) {
            return ResponseEntity.badRequest()
                    .body(errorResponse("Field 'transactionId' is required"));
        }

        log.info("[DEPOSIT_PROMO] Manual apply request: transactionId={}, amount={}",
                event.getTransactionId(), event.getAmount());

        boolean applied = depositPromotionService.evaluateAndApply(event);

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("transactionId",   event.getTransactionId());
        response.put("depositAmount",   event.getAmount());
        response.put("applied",         applied);
        response.put("bonus",           applied ? DepositPromotionService.BONUS_AMOUNT : BigDecimal.ZERO);
        response.put("campaignCode",    DepositPromotionService.CAMPAIGN_CODE);
        response.put("message", applied
                ? String.format("$%.2f deposit bonus successfully applied to transaction %s",
                        DepositPromotionService.BONUS_AMOUNT, event.getTransactionId())
                : "Promotion not applied — check campaign window, transaction type, or amount threshold");

        return ResponseEntity.ok(response);
    }

    // ─────────────────────────────────────────────────────────────────────
    // GET /promotions/deposit/status
    // ─────────────────────────────────────────────────────────────────────

    /**
     * Returns the current status of the deposit promotion campaign.
     *
     * Response example:
     * {
     *   "campaignCode":  "DEPOSIT_BONUS_JUL_AUG_2026",
     *   "found":         true,
     *   "dbStatus":      "ACTIVE",
     *   "startDate":     "2026-07-23T06:59",
     *   "endDate":       "2026-08-23T23:59:59",
     *   "currentTime":   "2026-07-23T18:31:46",
     *   "withinWindow":  true,
     *   "active":        true,
     *   "minDeposit":    100.00,
     *   "bonusAmount":   2.00,
     *   "quotaUsed":     0,
     *   "quotaLimit":    null,
     *   "message":       "Campaign is ACTIVE and accepting deposits"
     * }
     */
    @GetMapping("/status")
    public ResponseEntity<CampaignStatusDto> getCampaignStatus() {
        log.debug("[DEPOSIT_PROMO] Status check requested");
        CampaignStatusDto status = depositPromotionService.getCampaignStatus();
        return ResponseEntity.ok(status);
    }

    // ─────────────────────────────────────────────────────────────────────
    // Private helpers
    // ─────────────────────────────────────────────────────────────────────

    private Map<String, Object> errorResponse(String message) {
        Map<String, Object> err = new LinkedHashMap<>();
        err.put("error", message);
        return err;
    }
}
